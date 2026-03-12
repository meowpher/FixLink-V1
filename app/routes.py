"""
Main Routes Blueprint - Student Portal and API Endpoints
"""
import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from werkzeug.utils import secure_filename
from . import db
from .models import Building, Floor, Room, Asset, Ticket, User
from .email_utils import send_ticket_email
from .auth_routes import user_login_required

main_bp = Blueprint('main', __name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main_bp.route('/')
def index():
    """Redirect to login page."""
    return redirect(url_for('auth.login'))


@main_bp.route('/report', methods=['GET'])
@user_login_required
def report_form():
    """
    Student portal - report room issues with visual map.
    Supports auto-selection via ?room=VY404 query parameter.
    """
    room_param = request.args.get('room', '').strip().upper()
    selected_building = None
    selected_floor = None
    selected_room = None
    
    # Parse room parameter (format: VY### or VY-###)
    if room_param:
        # Remove any hyphen
        room_param = room_param.replace('-', '')
        
        # Look for room number pattern VY###
        if room_param.startswith('VY') and len(room_param) >= 4:
            room_number = room_param
            
            # Find the room
            room = Room.query.filter(Room.number == room_number).first()
            if room:
                selected_room = room.id
                selected_floor = room.floor_id
                selected_building = room.floor.building_id if room.floor else None
    
    # Get Vyas building and floors
    building = Building.query.filter_by(name='Vyas').first()
    floors = []
    if building:
        floors = Floor.query.filter_by(building_id=building.id).order_by(Floor.level).all()
        selected_building = building.id
    
    issue_types = [
        ('electrical', 'Electrical Issue'),
        ('plumbing', 'Plumbing Issue'),
        ('furniture', 'Furniture/Bench Damage'),
        ('projector', 'Projector/AV Equipment'),
        ('ac', 'Air Conditioning'),
        ('lighting', 'Lighting'),
        ('computer', 'Computer/Lab Equipment'),
        ('cleaning', 'Cleaning Required'),
        ('lift_breakdown', 'Lift Not Working'),
        ('door_error', 'Door Error'),
        ('light_broken', 'Light/Fan Broken'),
        ('other', 'Other')
    ]
    
    user = User.query.get(session['user_id'])
    
    return render_template('report.html',
                         user=user,
                         building=building,
                         floors=floors,
                         issue_types=issue_types,
                         selected_building=selected_building,
                         selected_floor=selected_floor,
                         selected_room=selected_room,
                         room_param=room_param)


@main_bp.route('/report', methods=['POST'])
@user_login_required
def submit_report():
    """
    Submit a new maintenance ticket.
    Handles both AJAX and form submissions.
    """
    user = User.query.get(session['user_id'])
    reporter_name = user.name
    prn = user.prn or 'Admin'
    reporter_email = user.email

    room_id = request.form.get('room_id')
    asset_id = request.form.get('asset_id')
    issue_type = request.form.get('issue_type', '').strip()
    description = request.form.get('description', '').strip()
    
    # Server-side validation
    errors = []
    
    if not room_id:
        errors.append('Room is required')
    
    if not issue_type:
        errors.append('Issue type is required')
    
    if not description:
        errors.append('Description is required')
    
    if errors:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'errors': errors}), 400
        return render_template('report.html', errors=errors), 400
    
    # Handle image upload
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid collisions
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_filename = filename
    
    try:
        # Create ticket
        ticket = Ticket(
            room_id=int(room_id),
            asset_id=int(asset_id) if asset_id else None,
            issue_type=issue_type,
            description=description,
            image_filename=image_filename,
            reporter_id=user.id,
            reporter_name=reporter_name,
            prn=prn,
            reporter_email=reporter_email.lower(),
            status=Ticket.STATUS_OPEN
        )
        
        db.session.add(ticket)
        
        # If asset specified, mark it as broken
        if asset_id:
            asset = Asset.query.get(int(asset_id))
            if asset:
                asset.status = Asset.STATUS_BROKEN
        
        db.session.commit()
        
        # Trigger EmailJS notification for ticket creation
        send_ticket_email(ticket, action='created')
        
        # Return JSON for AJAX, redirect for form submission
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'ticket_id': ticket.id,
                'message': 'Ticket submitted successfully'
            })
        
        return render_template('report.html', 
                             success=True, 
                             ticket_id=ticket.id,
                             building=Building.query.filter_by(name='Vyas').first())
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'errors': [error_msg]}), 500
        return render_template('report.html', errors=[error_msg]), 500


# API Endpoints

@main_bp.route('/api/floors/<int:building_id>', methods=['GET'])
def get_floors(building_id):
    """Get all floors for a building (JSON)."""
    floors = Floor.query.filter_by(building_id=building_id).order_by(Floor.level).all()
    return jsonify({
        'success': True,
        'floors': [floor.to_dict() for floor in floors]
    })


@main_bp.route('/api/rooms/floor/<int:floor_id>', methods=['GET'])
def get_rooms_by_floor(floor_id):
    """Get all rooms for a floor (JSON)."""
    rooms = Room.query.filter_by(floor_id=floor_id).all()
    return jsonify({
        'success': True,
        'rooms': [{
            **room.to_dict(),
            'status': room.status,
            'has_open_tickets': room.has_open_tickets
        } for room in rooms]
    })


@main_bp.route('/api/room/<room_number>', methods=['GET'])
def get_room_by_number(room_number):
    """Get room details by room number (JSON)."""
    room = Room.query.filter_by(number=room_number.upper()).first()
    if not room:
        return jsonify({'success': False, 'error': 'Room not found'}), 404
    
    return jsonify({
        'success': True,
        'room': {
            **room.to_dict(),
            'status': room.status,
            'has_open_tickets': room.has_open_tickets
        }
    })


@main_bp.route('/api/assets/<int:room_id>', methods=['GET'])
def get_assets(room_id):
    """Get all assets for a room (JSON)."""
    assets = Asset.query.filter_by(room_id=room_id).all()
    return jsonify({
        'success': True,
        'assets': [asset.to_dict() for asset in assets]
    })


@main_bp.route('/api/buildings', methods=['GET'])
def get_buildings():
    """Get all buildings (JSON)."""
    buildings = Building.query.all()
    return jsonify({
        'success': True,
        'buildings': [building.to_dict() for building in buildings]
    })


@main_bp.route('/api/me')
@user_login_required
def get_me():
    """Return current user's profile info for the navbar avatar."""
    user = User.query.get(session['user_id'])
    photo_url = (
        url_for('static', filename=f'uploads/{user.profile_photo}')
        if user and user.profile_photo else None
    )
    return jsonify({
        'success': True,
        'name': user.name if user else '',
        'email': user.email if user else '',
        'prn': user.prn or 'Admin' if user else '',
        'photo_url': photo_url
    })
