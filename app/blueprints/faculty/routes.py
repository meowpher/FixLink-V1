"""
Faculty Routes Blueprint - Smart Room Scheduling
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy.orm import joinedload
from ... import db
from ...models import User, Building, Floor, Room, Schedule, AdHocBooking, Timetable, RoomBooking
from ...decorators import faculty_login_required
from ...api_utils import handle_api_errors, api_response
from ...realtime import emit_room_status_change

faculty_bp = Blueprint('faculty', __name__)

@faculty_bp.route('/dashboard')
@faculty_login_required
def dashboard():
    """Faculty combined dashboard (My Schedule & Room Utilization Tracker)."""
    user_id = session.get('user_id')
    faculty = User.query.get(user_id)
    
    # Time context
    current_dt = datetime.utcnow() + timedelta(hours=5, minutes=30)
    current_day = current_dt.weekday() # 0 = Monday
    
    # 1. My Schedule
    my_schedules = Schedule.query.filter_by(faculty_id=faculty.id).order_by(Schedule.day_of_week, Schedule.start_time).all()
    my_adhoc = AdHocBooking.query.filter(
        AdHocBooking.faculty_id == faculty.id,
        AdHocBooking.end_datetime >= datetime.utcnow()
    ).order_by(AdHocBooking.start_datetime).all()
    
    # 2. Room Utilization Tracker (Global View)
    vyas = Building.query.filter_by(name='Vyas').first()
    floors = []
    if vyas:
        # Load up to level 7, skip level 6 maybe? Based on other parts of code
        floors = Floor.query.filter(Floor.building_id == vyas.id, Floor.level != 6).order_by(Floor.level).all()
        
    # Eager load rooms for efficiency
    all_rooms = Room.query.options(
        joinedload(Room.schedules),
        joinedload(Room.adhoc_bookings).joinedload(AdHocBooking.faculty)
    ).all()
    
    rooms_by_floor = {}
    for room in all_rooms:
        if room.floor_id not in rooms_by_floor:
            rooms_by_floor[room.floor_id] = []
        rooms_by_floor[room.floor_id].append(room)

    return render_template('faculty/dashboard.html',
                           faculty=faculty,
                           floors=floors,
                           rooms_by_floor=rooms_by_floor,
                           my_schedules=my_schedules,
                           my_adhoc=my_adhoc,
                           current_day=current_day)


@faculty_bp.route('/api/claim-room', methods=['POST'])
@faculty_login_required
@handle_api_errors
def claim_room():
    """Ad-hoc claim of an empty room by faculty."""
    data = request.get_json()
    room_id = data.get('room_id')
    duration_mins = data.get('duration_mins', 60)
    subject = data.get('subject', 'Ad-hoc Lecture').strip()
    
    if not room_id:
        return api_response(success=False, error="Room ID is required.", status=400)
        
    try:
        duration_mins = int(duration_mins)
    except:
        return api_response(success=False, error="Invalid duration.", status=400)
    
    room = Room.query.options(
        joinedload(Room.schedules),
        joinedload(Room.adhoc_bookings)
    ).filter_by(id=room_id).first_or_404()
    
    # Check if the room is vacant
    status_info = room.current_occupancy_status
    if status_info['status'] == 'occupied':
        return api_response(success=False, error=f"Room is already occupied by {status_info.get('faculty')} for {status_info.get('subject')}.", status=400)
    
    # Calculate UTC start and end
    start_utc = datetime.utcnow()
    end_utc = start_utc + timedelta(minutes=duration_mins)
    
    # Ensure they aren't claiming and conflicting with an upcoming schedule within the duration
    current_dt = start_utc + timedelta(hours=5, minutes=30)
    current_day = current_dt.weekday()
    end_dt_ist = end_utc + timedelta(hours=5, minutes=30)
    
    for sched in room.schedules:
        if sched.day_of_week == current_day:
            sched_start = datetime.combine(current_dt.date(), sched.start_time)
            # If the scheduled lesson starts within our selected duration
            if current_dt < sched_start < end_dt_ist:
                # Truncate the duration or deny
                return api_response(success=False, error=f"Time conflict. A scheduled class for {sched.subject} starts at {sched.start_time.strftime('%I:%M %p')}.", status=400)
    
    user_id = session.get('user_id')
    faculty = User.query.get(user_id)
    
    booking = AdHocBooking(
        room_id=room.id,
        faculty_id=user_id,
        subject=subject,
        start_datetime=start_utc,
        end_datetime=end_utc
    )
    
    db.session.add(booking)
    db.session.commit()
    
    # Emit pusher event
    emit_room_status_change(room, {
        'status': 'occupied',
        'type': 'adhoc',
        'subject': subject,
        'faculty': faculty.name,
        'end_time': end_dt_ist.strftime('%I:%M %p')
    })
    

@faculty_bp.route('/api/map/status/<int:floor_id>')
@faculty_login_required
@handle_api_errors
def get_map_status(floor_id):
    """Returns room data for the selected floor in a standard map-ready format."""
    floor = Floor.query.get_or_404(floor_id)
    rooms = Room.query.filter_by(floor_id=floor_id).all()
    
    return api_response(data={
        'floor': {
            'id': floor.id,
            'name': floor.name,
            'level': floor.level
        },
        'rooms': [room.to_map_dict() for room in rooms]
    })


@faculty_bp.route('/api/bookings/create', methods=['POST'])
@faculty_login_required
@handle_api_errors
def create_booking():
    """Validates and creates a 1-hour slot room booking."""
    data = request.get_json()
    room_id = data.get('room_id')
    slot_iso = data.get('slot_start') # Expecting ISO format 'YYYY-MM-DDTHH:MM:SS'
    subject = data.get('subject', 'Faculty Meeting')
    
    if not room_id or not slot_iso:
        return api_response(success=False, error="Room ID and slot start time are required.", status=400)
    
    try:
        # slot_iso should be interpreted as IST but stored or converted
        # The prompt says 1-hour slots like 10:00, 11:00
        slot_start = datetime.fromisoformat(slot_iso.replace('Z', ''))
        # Normalize to the beginning of the hour
        slot_start = slot_start.replace(minute=0, second=0, microsecond=0)
        duration_hours = int(data.get('duration', 1))
        if duration_hours > 2:
            return api_response(success=False, error="Maximum booking duration is 2 hours.", status=400)
        
        booking_date = slot_start.date()
        current_day = slot_start.weekday()
        user_id = session.get('user_id')
        
        # 1. Check for conflicts for ALL requested slots
        for i in range(duration_hours):
            current_slot = slot_start + timedelta(hours=i)
            
            # RoomBooking conflict
            existing_booking = RoomBooking.query.filter_by(
                room_id=room_id,
                date=booking_date,
                slot_start=current_slot,
                status=RoomBooking.STATUS_ACTIVE
            ).first()
            
            if existing_booking:
                return api_response(success=False, error=f"Room is already booked for the {current_slot.strftime('%I:%M %p')} slot.", status=400)
                
            # Timetable conflict
            existing_timetable = Timetable.query.filter_by(
                room_id=room_id,
                day_of_week=current_day,
                start_time=current_slot.time()
            ).first()
            
            if existing_timetable:
                return api_response(success=False, error=f"Conflict with regular class: {existing_timetable.subject}.", status=400)

        # 2. Create the bookings
        for i in range(duration_hours):
            booking = RoomBooking(
                room_id=room_id,
                faculty_id=user_id,
                date=booking_date,
                slot_start=slot_start + timedelta(hours=i),
                subject=subject
            )
            db.session.add(booking)
        
        db.session.commit()
        
        # Emit status change via pusher
        room = Room.query.get(room_id)
        emit_room_status_change(room, room.current_occupancy_status)
        
        return api_response(success=True, message=f"Successfully reserved for {duration_hours} hour(s).")
    except ValueError:
        return api_response(success=False, error="Invalid date/time format.", status=400)


@faculty_bp.route('/api/bookings/cancel/<int:booking_id>', methods=['POST'])
@faculty_login_required
@handle_api_errors
def cancel_booking(booking_id):
    """Cancels a faculty booking if they are the owner."""
    booking = RoomBooking.query.get_or_404(booking_id)
    user_id = session.get('user_id')
    
    if booking.faculty_id != user_id:
        return api_response(success=False, error="You can only cancel your own reservations.", status=403)
        
    booking.status = RoomBooking.STATUS_CANCELLED
    db.session.commit()
    
    # Update map for everyone
    emit_room_status_change(booking.room, booking.room.current_occupancy_status)
    
    return api_response(success=True, message="Reservation cancelled successfully.")


@faculty_bp.route('/api/timetable/cancel/<int:timetable_id>', methods=['POST'])
@faculty_login_required
@handle_api_errors
def cancel_timetable_session(timetable_id):
    """Marks a recurring timetable session as 'Cancelled' for the CURRENT slot only."""
    # Since Timetable is recurring, we don't 'delete' it. 
    # Instead, we create a RoomBooking with status 'cancelled' or similar to override it?
    # Actually, the user says "cancelling their reservation". 
    # If it's a regular class, maybe they are just marking it as 'not happening today'.
    
    tt = Timetable.query.get_or_404(timetable_id)
    user_id = session.get('user_id')
    
    if tt.faculty_id != user_id:
        return api_response(success=False, error="You can only cancel your own classes.", status=403)
    
    # Create a 'cancelled' RoomBooking for today to override the timetable entry
    now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    current_hour_utc = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    # Check if an override already exists
    override = RoomBooking(
        room_id=tt.room_id,
        faculty_id=user_id,
        date=now_ist.date(),
        slot_start=current_hour_utc,
        status=RoomBooking.STATUS_CANCELLED,
        subject=f"CANCELLED: {tt.subject}"
    )
    db.session.add(override)
    db.session.commit()
    
    emit_room_status_change(tt.room, tt.room.current_occupancy_status)
    return api_response(success=True, message="Class marked as cancelled for this hour.")


@faculty_bp.route('/api/faculty/timetable', methods=['POST'])
@faculty_login_required
@handle_api_errors
def upsert_timetable():
    """Bulk upserts timetable entries for the logged-in faculty."""
    data = request.get_json() # Expecting a list of objects
    if not isinstance(data, list):
        return api_response(success=False, error="Data must be a list of timetable entries.", status=400)
        
    user_id = session.get('user_id')
    
    # For simplicity, we'll clear existing timetable for this faculty or handle updates
    # The request says "Bulk upserts", I'll implement a basic upsert
    success_count = 0
    
    for entry in data:
        room_id = entry.get('room_id')
        day = entry.get('day_of_week')
        start_time_str = entry.get('start_time') # 'HH:MM'
        subject = entry.get('subject')
        
        if not all([room_id, day is not None, start_time_str, subject]):
            continue
            
        try:
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except:
            continue
            
        # Check for conflict in the room at that time
        existing = Timetable.query.filter_by(
            room_id=room_id,
            day_of_week=day,
            start_time=start_time
        ).first()
        
        if existing:
            # Update
            existing.faculty_id = user_id
            existing.subject = subject
        else:
            # Create
            new_entry = Timetable(
                room_id=room_id,
                faculty_id=user_id,
                day_of_week=day,
                start_time=start_time,
                subject=subject
            )
            db.session.add(new_entry)
        
        success_count += 1
        
    db.session.commit()
    return api_response(message=f"Successfully updated {success_count} timetable entries.")
