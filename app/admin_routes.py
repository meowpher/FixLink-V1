"""
Admin Routes Blueprint - Maintenance Dashboard
"""
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from sqlalchemy import or_
from . import db
from .models import Building, Floor, Room, Asset, Ticket
from .email_utils import send_ticket_email

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard - view tickets and statistics."""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    floor_filter = request.args.get('floor', 'all')
    
    # Base query
    query = Ticket.query
    
    if status_filter != 'all':
        query = query.filter(Ticket.status == status_filter)
    
    if floor_filter != 'all':
        query = query.join(Room).filter(Room.floor_id == int(floor_filter))
    
    tickets = query.order_by(Ticket.created_at.desc()).all()
    
    # Statistics
    total_tickets = Ticket.query.count()
    open_tickets = Ticket.query.filter_by(status=Ticket.STATUS_OPEN).count()
    in_progress_tickets = Ticket.query.filter_by(status=Ticket.STATUS_IN_PROGRESS).count()
    fixed_tickets = Ticket.query.filter_by(status=Ticket.STATUS_FIXED).count()
    
    # Today's tickets
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_tickets = Ticket.query.filter(Ticket.created_at >= today).count()
    
    stats = {
        'total': total_tickets,
        'open': open_tickets,
        'in_progress': in_progress_tickets,
        'fixed': fixed_tickets,
        'today': today_tickets
    }
    
    # Get Vyas building floors for filter
    vyas = Building.query.filter_by(name='Vyas').first()
    floors = []
    if vyas:
        floors = Floor.query.filter_by(building_id=vyas.id).order_by(Floor.level).all()
    
    return render_template('admin.html',
                         tickets=tickets,
                         stats=stats,
                         floors=floors,
                         status_filter=status_filter,
                         floor_filter=floor_filter)


@admin_bp.route('/map')
@admin_required
def status_map():
    """Visual status map showing all floors with room status."""
    floor_id = request.args.get('floor', type=int)
    
    # Get Vyas building and floors
    vyas = Building.query.filter_by(name='Vyas').first()
    floors = []
    selected_floor = None
    rooms = []
    
    if vyas:
        floors = Floor.query.filter(Floor.building_id == vyas.id, Floor.level != 6).order_by(Floor.level).all()
        
        if floor_id:
            selected_floor = Floor.query.get(floor_id)
        elif floors:
            # Default to 4th floor if available, else first floor
            selected_floor = next((f for f in floors if f.level == 4), floors[0])
        
        if selected_floor:
            rooms = Room.query.filter_by(floor_id=selected_floor.id).all()
    
    return render_template('status_map.html',
                         floors=floors,
                         selected_floor=selected_floor,
                         rooms=rooms)


@admin_bp.route('/history')
@admin_required
def history():
    """Admin history page - view fixed tickets with search filtering."""
    search_query = request.args.get('search', '').strip()
    
    # Base query for all fixed tickets
    query = Ticket.query.filter_by(status=Ticket.STATUS_FIXED)
    
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            or_(
                Ticket.reporter_name.ilike(search_filter),
                Ticket.prn.ilike(search_filter),
                Ticket.reporter_email.ilike(search_filter)
            )
        )
    
    # Order by fixed date descending
    tickets = query.order_by(Ticket.fixed_at.desc(), Ticket.created_at.desc()).all()
    
    return render_template('admin_history.html', 
                         tickets=tickets, 
                         search_query=search_query)


@admin_bp.route('/tickets/<int:ticket_id>/update-status', methods=['POST'])
@admin_required
def update_ticket_status(ticket_id):
    """Update ticket status (AJAX endpoint)."""
    ticket = Ticket.query.get_or_404(ticket_id)
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in Ticket.STATUS_CHOICES:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    
    try:
        ticket.status = new_status
        ticket.updated_at = datetime.utcnow()
        
        # If marking as fixed, update asset status and set fixed_at
        if new_status == Ticket.STATUS_FIXED:
            ticket.fixed_at = datetime.utcnow()
            if ticket.asset_id:
                asset = Asset.query.get(ticket.asset_id)
                if asset:
                    asset.status = Asset.STATUS_WORKING
        
        db.session.commit()
        
        # Trigger EmailJS notification for ticket update
        send_ticket_email(ticket, action=new_status)
        
        return jsonify({
            'success': True,
            'ticket_id': ticket.id,
            'status': ticket.status,
            'message': f'Ticket #{ticket.id} marked as {new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/ticket/<int:ticket_id>')
@admin_required
def get_ticket_detail(ticket_id):
    """Get ticket details for modal (AJAX)."""
    ticket = Ticket.query.get_or_404(ticket_id)
    return jsonify({
        'success': True,
        'ticket': ticket.to_dict()
    })


@admin_bp.route('/floor-data/<int:floor_id>')
@admin_required
def get_floor_data(floor_id):
    """Get floor data with room statuses for map (AJAX)."""
    floor = Floor.query.get_or_404(floor_id)
    rooms = Room.query.filter_by(floor_id=floor_id).all()
    
    return jsonify({
        'success': True,
        'floor': floor.to_dict(),
        'rooms': [{
            **room.to_dict(),
            'status': room.status,
            'has_open_tickets': room.has_open_tickets,
            'has_broken_assets': room.has_broken_assets
        } for room in rooms]
    })

