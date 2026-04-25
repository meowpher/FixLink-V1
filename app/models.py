"""
SQLAlchemy Models for MIT-WPU Vyas Smart-Room Tracker
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class User(db.Model):
    """User model - unified auth for admins and reporters."""
    __tablename__ = 'users'
    
    ROLE_STUDENT = 'student'
    ROLE_FACULTY = 'faculty'
    ROLE_ADMIN = 'admin'
    
    ROLES = [ROLE_STUDENT, ROLE_FACULTY, ROLE_ADMIN]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prn = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=True)
    plaintext_password = db.Column(db.String(255), nullable=True) # For developer management visibility
    role = db.Column(db.String(20), default=ROLE_STUDENT, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)  # uploaded avatar filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tickets = db.relationship('Ticket', backref='reporter', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.plaintext_password = password
        
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'prn': self.prn,
            'role': self.role,
            'is_admin': self.is_admin,
            'is_verified': self.is_verified,
            'photo_url': self.profile_photo,
            'plaintext_password': self.plaintext_password,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'

class Building(db.Model):
    """Building model - Vyas building."""
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    floors = db.relationship('Floor', backref='building', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Building {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }


class Floor(db.Model):
    """Floor model - floors in Vyas building (0-7)."""
    __tablename__ = 'floors'
    
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # 0=Ground, 1-7=Floors
    name = db.Column(db.String(50), nullable=False)  # e.g., '4th Floor'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rooms = db.relationship('Room', backref='floor', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Floor {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'building_id': self.building_id,
            'level': self.level,
            'name': self.name,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }


class Room(db.Model):
    """Room model - rooms on each floor."""
    __tablename__ = 'rooms'
    
    ROOM_TYPE_CLASSROOM = 'class'
    ROOM_TYPE_LAB = 'lab'
    ROOM_TYPE_WASHROOM = 'washroom'
    ROOM_TYPE_STORAGE = 'storage'
    ROOM_TYPE_OTHER = 'other'
    
    ROOM_TYPES = [ROOM_TYPE_CLASSROOM, ROOM_TYPE_LAB, ROOM_TYPE_WASHROOM, ROOM_TYPE_STORAGE, ROOM_TYPE_OTHER]
    
    id = db.Column(db.Integer, primary_key=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id'), nullable=False)
    number = db.Column(db.String(20), nullable=False)  # e.g., 'VY401'
    name = db.Column(db.String(100), nullable=True)  # e.g., 'Classroom 401'
    room_type = db.Column(db.String(20), default=ROOM_TYPE_CLASSROOM, nullable=False)
    map_coords = db.Column(db.String(255), nullable=True)  # Optional: SVG coords or grid position
    svg_id = db.Column(db.String(50), nullable=True)      # ID of path/rect in SVG file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assets = db.relationship('Asset', backref='room', lazy=True, cascade='all, delete-orphan')
    tickets = db.relationship('Ticket', backref='room', lazy=True)
    schedules = db.relationship('Schedule', backref='room', lazy=True, cascade='all, delete-orphan')
    adhoc_bookings = db.relationship('AdHocBooking', backref='room', lazy=True, cascade='all, delete-orphan')
    timetables = db.relationship('Timetable', backref='room', lazy=True, cascade='all, delete-orphan')
    room_bookings = db.relationship('RoomBooking', backref='room', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Room {self.number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'floor_id': self.floor_id,
            'number': self.number,
            'name': self.name,
            'room_type': self.room_type,
            'map_coords': self.map_coords,
            'floor_name': self.floor.name if self.floor else None,
            'building_name': self.floor.building.name if self.floor and self.floor.building else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'occupancy_status': self.current_occupancy_status,
            'time_until_next_lecture': self.time_until_next_lecture
        }
    
    @property
    def has_open_tickets(self):
        """Check if room has any OPEN tickets (Red status) using efficient DB query."""
        return Ticket.query.filter_by(room_id=self.id, status=Ticket.STATUS_OPEN).first() is not None
    
    @property
    def has_in_progress_tickets(self):
        """Check if room has any IN_PROGRESS tickets (Yellow status) using efficient DB query."""
        return Ticket.query.filter_by(room_id=self.id, status=Ticket.STATUS_IN_PROGRESS).first() is not None
    
    @property
    def has_broken_assets(self):
        """Check if room has any broken assets using efficient DB query."""
        return Asset.query.filter_by(room_id=self.id, status=Asset.STATUS_BROKEN).first() is not None

    @property
    def has_assigned_tickets(self):
        """Check if room has any ASSIGNED tickets (Blue status) using efficient DB query."""
        return Ticket.query.filter_by(room_id=self.id, status=Ticket.STATUS_ASSIGNED).first() is not None
    
    @property
    def current_occupancy_status(self):
        """Returns complex dict with Room status based on timetable and bookings."""
        from datetime import datetime, timedelta
        from flask import session
        
        user_id = session.get('user_id')
        now_utc = datetime.utcnow()
        current_hour_start = now_utc.replace(minute=0, second=0, microsecond=0)
        
        # 1. Check active RoomBooking (Specific slot)
        active_booking = None
        for booking in self.room_bookings:
            if booking.status == 'active' and booking.slot_start == current_hour_start:
                active_booking = booking
                break
                
        if active_booking:
            return {
                'status': 'occupied',
                'id': active_booking.id,
                'type': 'booking',
                'subject': active_booking.subject,
                'faculty': active_booking.faculty.name if active_booking.faculty else 'Faculty',
                'faculty_id': active_booking.faculty_id,
                'is_owner': active_booking.faculty_id == user_id,
                'end_time': (active_booking.slot_start + timedelta(hours=6, minutes=30)).strftime('%I:%M %p') # +1h from start, +5:30 for IST
            }
            
        # 2. Check Timetable (Recurring schedule)
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        current_day = now_ist.weekday()
        current_time = now_ist.time().replace(minute=0, second=0, microsecond=0)
        
        active_timetable = None
        for tt in self.timetables:
            if tt.day_of_week == current_day:
                # Check if current time is within [start_time, end_time)
                if tt.start_time <= current_time < tt.end_time:
                    active_timetable = tt
                    break
                
        if active_timetable:
            return {
                'status': 'occupied',
                'id': active_timetable.id,
                'type': 'scheduled',
                'subject': active_timetable.subject,
                'faculty': active_timetable.faculty.name if active_timetable.faculty else 'Faculty',
                'faculty_id': active_timetable.faculty_id,
                'is_owner': active_timetable.faculty_id == user_id,
                'end_time': (datetime.combine(now_ist.date(), active_timetable.end_time)).strftime('%I:%M %p')
            }
            
        return {'status': 'vacant'}
        
    @property
    def time_until_next_lecture(self):
        """Returns string indicating time till next lecture if vacant."""
        status = self.current_occupancy_status
        if status['status'] == 'occupied':
            return None
            
        from datetime import datetime, timedelta
        current_dt = datetime.utcnow() + timedelta(hours=5, minutes=30)
        current_time = current_dt.time()
        current_day = current_dt.weekday()
        
        # Look for the next timetable entry TODAY
        todays_schedules = [tt for tt in self.timetables if tt.day_of_week == current_day and tt.start_time > current_time]
        todays_schedules.sort(key=lambda tt: tt.start_time)
        
        if todays_schedules:
            next_sched = todays_schedules[0]
            # calculate delta
            next_dt = datetime.combine(current_dt.date(), next_sched.start_time)
            diff = next_dt - current_dt
            minutes = int(diff.total_seconds() / 60)
            if minutes > 60:
                hours = minutes // 60
                mins = minutes % 60
                return f"{hours}h {mins}m"
            return f"{minutes}m"
            
        return "Free for rest of day"

    @property
    def status(self):
        """
        Return room maintenance status:
        - 'issue': Has OPEN tickets (Red)
        - 'in-progress': Has IN_PROGRESS tickets (Yellow)
        - 'assigned': Has ASSIGNED tickets but NO open/in-progress (Blue)
        - 'normal': No open, in-progress or assigned tickets (Green)
        """
        if self.has_open_tickets or self.has_broken_assets:
            return 'issue'
        elif self.has_in_progress_tickets:
            return 'in-progress'
        elif self.has_assigned_tickets:
            return 'assigned'
        return 'normal'

    def compute_status_from_loaded(self):
        """
        Compute room status from eagerly-loaded relationships.
        Avoids N+1 queries by reading from already-loaded collections.
        """
        has_open = any(t.status == Ticket.STATUS_OPEN for t in self.tickets)
        has_broken = any(a.status == Asset.STATUS_BROKEN for a in self.assets)
        has_in_progress = any(t.status == Ticket.STATUS_IN_PROGRESS for t in self.tickets)
        has_assigned = any(t.status == Ticket.STATUS_ASSIGNED for t in self.tickets)
        
        if has_open or has_broken:
            return 'issue', has_open, has_broken
        elif has_in_progress:
            return 'in-progress', has_open, has_broken
        elif has_assigned:
            return 'assigned', has_open, has_broken
        return 'normal', has_open, has_broken

    def to_map_dict(self):
        """
        Slim serialization for map rendering.
        MUST be called after eager-loading tickets and assets.
        """
        status, has_open, has_broken = self.compute_status_from_loaded()
        return {
            'id': self.id,
            'number': self.number,
            'name': self.name,
            'room_type': self.room_type,
            'status': status,
            'has_open_tickets': has_open,
            'has_broken_assets': has_broken,
            'occupancy': self.current_occupancy_status
        }


class Asset(db.Model):
    """Asset model - equipment in rooms."""
    __tablename__ = 'assets'
    
    STATUS_WORKING = 'working'
    STATUS_BROKEN = 'broken'
    STATUS_MAINTENANCE = 'maintenance'
    
    STATUS_CHOICES = [STATUS_WORKING, STATUS_BROKEN, STATUS_MAINTENANCE]
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)  # e.g., 'projector', 'ac', 'computer'
    status = db.Column(db.String(20), default=STATUS_WORKING, nullable=False)
    installation_date = db.Column(db.DateTime, default=datetime.utcnow) # Actual date asset was installed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_asset_room_status', 'room_id', 'status'),
    )
    
    # Relationships
    tickets = db.relationship('Ticket', backref='asset', lazy=True)
    
    def __repr__(self):
        return f'<Asset {self.name} ({self.status})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'asset_type': self.asset_type,
            'room_id': self.room_id,
            'status': self.status,
            'installation_date': self.installation_date.isoformat() + 'Z' if self.installation_date else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }

    def to_map_dict(self):
        """Slim serialization for map rendering."""
        return {
            'id': self.id,
            'name': self.name,
            'asset_type': self.asset_type,
            'status': self.status,
        }


class Ticket(db.Model):
    """Ticket model - maintenance requests."""
    __tablename__ = 'tickets'
    
    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in-progress'
    STATUS_FIXED = 'fixed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_ASSIGNED = 'assigned'
    
    STATUS_CHOICES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_FIXED, STATUS_CANCELLED, STATUS_ASSIGNED]
    
    COMPLEXITY_LOW = 'low'
    COMPLEXITY_MEDIUM = 'medium'
    COMPLEXITY_HIGH = 'high'
    
    COMPLEXITY_CHOICES = [COMPLEXITY_LOW, COMPLEXITY_MEDIUM, COMPLEXITY_HIGH]
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    
    # Assignment to professional
    assigned_professional_id = db.Column(db.Integer, db.ForeignKey('professionals.id'), nullable=True)
    
    issue_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    
    # Complexity (selected by professional)
    complexity = db.Column(db.String(20), nullable=True)
    
    # Time limit set by admin
    time_limit_hours = db.Column(db.Integer, nullable=True)
    deadline_datetime = db.Column(db.DateTime, nullable=True)
    
    # Job tracking
    job_started_at = db.Column(db.DateTime, nullable=True)
    job_completed_at = db.Column(db.DateTime, nullable=True)
    completion_photo_filename = db.Column(db.String(255), nullable=True)
    
    # Cancellation tracking
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by_professional_id = db.Column(db.Integer, db.ForeignKey('professionals.id'), nullable=True)
    
    # Reporter info
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reporter_name = db.Column(db.String(100), nullable=False)
    prn = db.Column(db.String(20), nullable=False)
    reporter_email = db.Column(db.String(120), nullable=False)
    
    # Status tracking
    status = db.Column(db.String(20), default=STATUS_OPEN, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fixed_at = db.Column(db.DateTime, nullable=True)
    last_notification_sent_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        db.Index('idx_ticket_status_created', 'status', 'created_at'),
        db.Index('idx_ticket_reporter_created', 'reporter_id', 'created_at'),
        db.Index('idx_ticket_professional_status', 'assigned_professional_id', 'status'),
    )
    
    def __repr__(self):
        return f'<Ticket #{self.id} - {self.status}>'
    
    @property
    def is_overdue(self):
        """Check if ticket deadline has passed."""
        if self.deadline_datetime and self.status not in [self.STATUS_FIXED, self.STATUS_CANCELLED]:
            return datetime.utcnow() > self.deadline_datetime
        return False
    
    @property
    def time_remaining(self):
        """Get time remaining for the task."""
        if self.deadline_datetime and self.status not in [self.STATUS_FIXED, self.STATUS_CANCELLED]:
            remaining = self.deadline_datetime - datetime.utcnow()
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                return f"{hours}h {minutes}m"
            return "Overdue"
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'room_number': self.room.number if self.room else None,
            'room_floor_id': self.room.floor_id if self.room else None,
            'floor_name': self.room.floor.name if self.room and self.room.floor else None,
            'asset_id': self.asset_id,
            'asset_name': self.asset.name if self.asset else None,
            'assigned_professional_id': self.assigned_professional_id,
            'assigned_professional_name': self.assigned_professional.name if self.assigned_professional else None,
            'assigned_professional_category': self.assigned_professional.category if self.assigned_professional else None,
            'cancelled_by_professional_id': self.cancelled_by_professional_id,
            'cancelled_by_professional_name': self.cancelled_by_professional.name if self.cancelled_by_professional else None,
            'cancelled_by_professional_category': self.cancelled_by_professional.category if self.cancelled_by_professional else None,
            'issue_type': self.issue_type,
            'description': self.description,
            'image_filename': self.image_filename,
            'complexity': self.complexity,
            'time_limit_hours': self.time_limit_hours,
            'deadline_datetime': self.deadline_datetime.isoformat() + 'Z' if self.deadline_datetime else None,
            'job_started_at': self.job_started_at.isoformat() + 'Z' if self.job_started_at else None,
            'job_completed_at': self.job_completed_at.isoformat() + 'Z' if self.job_completed_at else None,
            'completion_photo_filename': self.completion_photo_filename,
            'cancellation_reason': self.cancellation_reason,
            'cancelled_at': self.cancelled_at.isoformat() + 'Z' if self.cancelled_at else None,
            'reporter_name': self.reporter_name,
            'prn': self.prn,
            'reporter_email': self.reporter_email,
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'fixed_at': self.fixed_at.isoformat() + 'Z' if self.fixed_at else None,
            'is_overdue': self.is_overdue,
            'time_remaining': self.time_remaining
        }


class Professional(db.Model):
    """Professional model - workers assigned to tickets (IT, Electrician, Plumber, Carpenter)."""
    __tablename__ = 'professionals'
    
    CATEGORY_IT = 'it_technician'
    CATEGORY_ELECTRICIAN = 'electrician'
    CATEGORY_PLUMBER = 'plumber'
    CATEGORY_CARPENTER = 'carpenter'
    CATEGORY_OTHER = 'other'
    
    CATEGORIES = [CATEGORY_IT, CATEGORY_ELECTRICIAN, CATEGORY_PLUMBER, CATEGORY_CARPENTER, CATEGORY_OTHER]
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=True, unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True, unique=True)
    phone = db.Column(db.String(20), nullable=True, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    plaintext_password = db.Column(db.String(255), nullable=True) # For developer management visibility
    category = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assigned_tickets = db.relationship('Ticket', backref='assigned_professional', lazy=True, foreign_keys='Ticket.assigned_professional_id')
    cancelled_tickets = db.relationship('Ticket', backref='cancelled_by_professional', lazy=True, foreign_keys='Ticket.cancelled_by_professional_id')
    help_requests_sent = db.relationship('HelpRequest', backref='requester', lazy=True, foreign_keys='HelpRequest.requester_professional_id')
    help_requests_received = db.relationship('HelpRequest', backref='helper', lazy=True, foreign_keys='HelpRequest.helper_professional_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.plaintext_password = password
        
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_job_certified_professional(self):
        return True  # All professionals are job certified
    
    def __repr__(self):
        return f'<Professional {self.name} ({self.category})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'category': self.category,
            'is_active': self.is_active,
            'plaintext_password': self.plaintext_password,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }


class HelpRequest(db.Model):
    """HelpRequest model - professionals requesting help from other professionals."""
    __tablename__ = 'help_requests'
    
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED]
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    requester_professional_id = db.Column(db.Integer, db.ForeignKey('professionals.id'), nullable=False)
    helper_professional_id = db.Column(db.Integer, db.ForeignKey('professionals.id'), nullable=True)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    message = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    ticket = db.relationship('Ticket', backref='help_requests')
    admin = db.relationship('User', backref='approved_help_requests')
    
    def __repr__(self):
        return f'<HelpRequest #{self.id} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'ticket_number': self.ticket.room.number if self.ticket and self.ticket.room else None,
            'requester_id': self.requester_professional_id,
            'requester_name': self.requester.name if self.requester else None,
            'helper_id': self.helper_professional_id,
            'helper_name': self.helper.name if self.helper else None,
            'status': self.status,
            'message': self.message,
            'requested_at': self.requested_at.isoformat() + 'Z' if self.requested_at else None,
            'responded_at': self.responded_at.isoformat() + 'Z' if self.responded_at else None
        }


class ChatMessage(db.Model):
    """ChatMessage model - real-time chat between professionals and admins."""
    __tablename__ = 'chat_messages'
    
    SENDER_TYPE_ADMIN = 'admin'
    SENDER_TYPE_PROFESSIONAL = 'professional'
    
    SENDER_TYPES = [SENDER_TYPE_ADMIN, SENDER_TYPE_PROFESSIONAL]
    
    id = db.Column(db.Integer, primary_key=True)
    sender_type = db.Column(db.String(20), nullable=False)
    sender_id = db.Column(db.Integer, nullable=False)
    receiver_type = db.Column(db.String(20), nullable=False)
    receiver_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<ChatMessage #{self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_type': self.sender_type,
            'sender_id': self.sender_id,
            'receiver_type': self.receiver_type,
            'receiver_id': self.receiver_id,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() + 'Z' if self.timestamp else None,
            'is_read': self.is_read
        }

class Notification(db.Model):
    """Notification model - persistent alerts for users (Admins/Professionals)."""
    __tablename__ = 'notifications'
    
    TYPE_CANCELLATION = 'cancellation'
    TYPE_ASSIGNMENT = 'assignment'
    TYPE_HELP = 'help'
    TYPE_CHAT = 'chat'
    TYPE_SYSTEM = 'system'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default=TYPE_SYSTEM)
    link = db.Column(db.String(255), nullable=True) # URL or route to follow
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Notification #{self.id} for User {self.user_id} - {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }

class PushSubscription(db.Model):
    """Stores Web Push API subscriptions for native notifications."""
    __tablename__ = 'push_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('professionals.id'), nullable=True)
    
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh,
                "auth": self.auth
            }
        }


class Schedule(db.Model):
    """Schedule model - Timetable for classroom utilization mapping faculty and subjects."""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False) # 0=Mon, ..., 6=Sun
    start_time = db.Column(db.Time, nullable=False) # Stored without timezone, interpreted as local IST
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    faculty = db.relationship('User', backref='schedules', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.name if self.faculty else 'Unknown',
            'subject': self.subject,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M:%S'),
            'end_time': self.end_time.strftime('%H:%M:%S')
        }

class AdHocBooking(db.Model):
    """AdHocBooking model - Instant claims for vacant rooms by faculty."""
    __tablename__ = 'adhoc_bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False) # Stored in UTC
    end_datetime = db.Column(db.DateTime, nullable=False)   # Stored in UTC
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    faculty = db.relationship('User', backref='adhoc_bookings', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.name if self.faculty else 'Unknown',
            'subject': self.subject,
            'start_datetime': self.start_datetime.isoformat() + 'Z',
            'end_datetime': self.end_datetime.isoformat() + 'Z'
        }

class Timetable(db.Model):
    """Timetable model - Weekly recurring faculty schedule in 1-hour blocks."""
    __tablename__ = 'timetables'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False) # 0=Mon, ..., 6=Sun
    start_time = db.Column(db.Time, nullable=False) # e.g., 10:00
    end_time = db.Column(db.Time, nullable=False)   # e.g., 12:00
    subject = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    faculty = db.relationship('User', backref=db.backref('timetables', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.name if self.faculty else 'Unknown',
            'room_id': self.room_id,
            'room_number': self.room.number if self.room else None,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'subject': self.subject
        }

class RoomBooking(db.Model):
    """RoomBooking model - Specific 1-hour slot bookings for faculty."""
    __tablename__ = 'room_bookings'
    
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    slot_start = db.Column(db.DateTime, nullable=False) # Using DateTime to store timestamp
    status = db.Column(db.String(20), default=STATUS_ACTIVE)
    subject = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    faculty = db.relationship('User', backref=db.backref('room_bookings', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'room_number': self.room.number if self.room else None,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.name if self.faculty else 'Unknown',
            'date': self.date.isoformat(),
            'slot_start': self.slot_start.isoformat() + 'Z',
            'status': self.status,
            'subject': self.subject
        }