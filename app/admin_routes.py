"""
Admin Routes Blueprint - Maintenance Dashboard
"""
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from sqlalchemy import or_
from . import db
from .models import Building, Floor, Room, Asset, Ticket, User, Professional, HelpRequest, ChatMessage
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
        if status_filter == 'open':
            query = query.filter(Ticket.status.in_([Ticket.STATUS_OPEN, Ticket.STATUS_CANCELLED]))
        else:
            query = query.filter(Ticket.status == status_filter)
    
    if floor_filter != 'all':
        query = query.join(Room).filter(Room.floor_id == int(floor_filter))
    
    tickets = query.order_by(Ticket.created_at.desc()).all()
    
    # Statistics
    total_tickets = Ticket.query.count()
    real_open = Ticket.query.filter_by(status=Ticket.STATUS_OPEN).count()
    real_cancelled = Ticket.query.filter_by(status=Ticket.STATUS_CANCELLED).count()
    assigned_tickets = Ticket.query.filter_by(status=Ticket.STATUS_ASSIGNED).count()
    in_progress_tickets = Ticket.query.filter_by(status=Ticket.STATUS_IN_PROGRESS).count()
    fixed_tickets = Ticket.query.filter_by(status=Ticket.STATUS_FIXED).count()
    
    # Today's tickets
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_tickets = Ticket.query.filter(Ticket.created_at >= today).count()
    
    stats = {
        'total': total_tickets,
        'open': real_open + real_cancelled, # Unified metric
        'assigned': assigned_tickets,
        'in_progress': in_progress_tickets,
        'fixed': fixed_tickets,
        'cancelled': real_cancelled,
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


@admin_bp.route('/users')
@admin_required
def users():
    """User Management page."""
    search_query = request.args.get('q', '').strip()
    role_filter = request.args.get('role', 'all')
    status_filter = request.args.get('status', 'all')
    sort_filter = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = User.query

    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            or_(
                User.name.ilike(search),
                User.email.ilike(search),
                User.prn.ilike(search)
            )
        )
    
    if role_filter == 'admin':
        query = query.filter_by(is_admin=True)
    elif role_filter == 'reporter':
        query = query.filter_by(is_admin=False)
        
    if status_filter == 'verified':
        query = query.filter_by(is_verified=True)
    elif status_filter == 'unverified':
        query = query.filter_by(is_verified=False)
        
    if sort_filter == 'newest':
        query = query.order_by(User.created_at.desc())
    elif sort_filter == 'oldest':
        query = query.order_by(User.created_at.asc())
    elif sort_filter == 'name':
        query = query.order_by(User.name.asc())
        
    total = query.count()
    users_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin_users.html',
                           users=users_paginated.items,
                           total=total,
                           page=page,
                           pages=users_paginated.pages,
                           per_page=per_page,
                           search_query=search_query,
                           role_filter=role_filter,
                           status_filter=status_filter,
                           sort=sort_filter)


@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    """Edit user details (AJAX)."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    if email != user.email:
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'Email already registered.'}), 400
            
    try:
        user.name = data.get('name', '').strip()
        user.email = email
        user.prn = data.get('prn', '').strip()
        user.is_admin = data.get('role') == 'admin'
        
        password = data.get('password')
        if password:
            user.set_password(password)
            
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user (AJAX)."""
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'error': 'Cannot delete yourself.'}), 400
        
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/users/<int:user_id>/verify', methods=['POST'])
@admin_required
def verify_user_manual(user_id):
    """Manually verify a user (AJAX)."""
    user = User.query.get_or_404(user_id)
    try:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


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


@admin_bp.route('/tickets/<int:ticket_id>/delete', methods=['POST'])
@admin_required
def delete_ticket(ticket_id):
    """Delete a ticket (AJAX endpoint)."""
    ticket = Ticket.query.get_or_404(ticket_id)
    try:
        # Delete associated image if it exists
        if ticket.image_filename:
            import os
            from flask import current_app
            file_path = os.path.join(current_app.root_path, 'static', 'uploads', ticket.image_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                
        db.session.delete(ticket)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Ticket #{ticket.id} deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== PROFESSIONAL MANAGEMENT ====================

@admin_bp.route('/professionals')
@admin_required
def professionals():
    """Professional Management page."""
    category_filter = request.args.get('category', 'all')
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Professional.query
    
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            or_(
                Professional.name.ilike(search),
                Professional.email.ilike(search),
                Professional.phone.ilike(search)
            )
        )
    
    if category_filter != 'all' and category_filter in Professional.CATEGORIES:
        query = query.filter_by(category=category_filter)
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    query = query.order_by(Professional.created_at.desc())
    
    total = query.count()
    professionals_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    return render_template('admin/professionals.html',
                         professionals=professionals_paginated.items,
                         total=total,
                         page=page,
                         pages=professionals_paginated.pages,
                         per_page=per_page,
                         search_query=search_query,
                         category_filter=category_filter,
                         status_filter=status_filter,
                         categories=Professional.CATEGORIES,
                         category_names=category_names)


@admin_bp.route('/professionals/<int:prof_id>/history')
@admin_required
def professional_history(prof_id):
    """View job history for a specific professional."""
    prof = Professional.query.get_or_404(prof_id)
    
    # Get completed jobs
    completed_jobs = Ticket.query.filter_by(
        assigned_professional_id=prof.id,
        status=Ticket.STATUS_FIXED
    ).order_by(Ticket.job_completed_at.desc()).all()
    
    # Get cancelled jobs
    cancelled_jobs = Ticket.query.filter_by(
        cancelled_by_professional_id=prof.id
    ).order_by(Ticket.cancelled_at.desc()).all()
    
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    return render_template('admin/professional_history.html',
                         professional=prof,
                         completed_jobs=completed_jobs,
                         cancelled_jobs=cancelled_jobs,
                         category_name=category_names.get(prof.category, prof.category))


@admin_bp.route('/professionals/add', methods=['GET', 'POST'])
@admin_required
def add_professional():
    """Add a new professional."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        category = request.form.get('category', '').strip()
        password = request.form.get('password', '').strip()
        
        if not all([name, email, category, password]):
            flash('Name, email, category, and password are required.', 'error')
            return render_template('admin/add_professional.html', 
                                 categories=Professional.CATEGORIES,
                                 form_data=request.form)
        
        if category not in Professional.CATEGORIES:
            flash('Invalid category selected.', 'error')
            return render_template('admin/add_professional.html',
                                 categories=Professional.CATEGORIES,
                                 form_data=request.form)
        
        if Professional.query.filter_by(email=email).first():
            flash('A professional with this email already exists.', 'error')
            return render_template('admin/add_professional.html',
                                 categories=Professional.CATEGORIES,
                                 form_data=request.form)
        
        try:
            professional = Professional(
                name=name,
                email=email,
                phone=phone,
                category=category,
                is_active=True
            )
            professional.set_password(password)
            db.session.add(professional)
            db.session.commit()
            
            flash(f'Professional {name} added successfully!', 'success')
            return redirect(url_for('admin.professionals'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding professional: {str(e)}', 'error')
    
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    return render_template('admin/add_professional.html',
                         categories=Professional.CATEGORIES,
                         category_names=category_names)


@admin_bp.route('/professionals/<int:professional_id>/edit', methods=['POST'])
@admin_required
def edit_professional(professional_id):
    """Edit professional details (AJAX)."""
    professional = Professional.query.get_or_404(professional_id)
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    if email != professional.email:
        if Professional.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'Email already registered.'}), 400
    
    try:
        professional.name = data.get('name', '').strip()
        professional.email = email
        professional.phone = data.get('phone', '').strip()
        
        new_category = data.get('category')
        if new_category in Professional.CATEGORIES:
            professional.category = new_category
        
        professional.is_active = data.get('is_active', professional.is_active)
        
        password = data.get('password')
        if password:
            professional.set_password(password)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/professionals/<int:professional_id>/delete', methods=['POST'])
@admin_required
def delete_professional(professional_id):
    """Delete a professional (AJAX)."""
    professional = Professional.query.get_or_404(professional_id)
    
    assigned_tickets = Ticket.query.filter_by(
        assigned_professional_id=professional_id
    ).filter(
        Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])
    ).count()
    
    if assigned_tickets > 0:
        return jsonify({
            'success': False, 
            'error': f'Cannot delete professional with {assigned_tickets} active tasks. Reassign tasks first.'
        }), 400
    
    try:
        db.session.delete(professional)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== TICKET ASSIGNMENT ====================

@admin_bp.route('/ticket/<int:ticket_id>/assign', methods=['GET', 'POST'])
@admin_required
def assign_ticket(ticket_id):
    """Assign a ticket to a professional."""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if request.method == 'POST':
        professional_id = request.form.get('professional_id', type=int)
        time_limit_hours = request.form.get('time_limit_hours', type=int)
        
        if not professional_id:
            flash('Please select a professional.', 'error')
            return redirect(url_for('admin.assign_ticket', ticket_id=ticket_id))
        
        if not time_limit_hours or time_limit_hours < 1:
            flash('Please enter a valid time limit (minimum 1 hour).', 'error')
            return redirect(url_for('admin.assign_ticket', ticket_id=ticket_id))
        
        professional = Professional.query.get(professional_id)
        if not professional or not professional.is_active:
            flash('Selected professional is not available.', 'error')
            return redirect(url_for('admin.assign_ticket', ticket_id=ticket_id))
        
        # Check if professional already has an active task
        active_task = Ticket.query.filter(
            Ticket.assigned_professional_id == professional_id,
            Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])
        ).first()
        
        if active_task:
            flash(f'{professional.name} already has an active task (# {active_task.id}). They must complete it before being assigned a new one.', 'error')
            return redirect(url_for('admin.assign_ticket', ticket_id=ticket_id))
        
        try:
            ticket.assigned_professional_id = professional_id
            ticket.time_limit_hours = time_limit_hours
            ticket.deadline_datetime = datetime.utcnow() + timedelta(hours=time_limit_hours)
            ticket.status = Ticket.STATUS_ASSIGNED
            db.session.commit()
            
            from .socket_events import notify_professional_assigned
            notify_professional_assigned(ticket, professional)
            
            flash(f'Ticket #{ticket_id} assigned to {professional.name}!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error assigning ticket: {str(e)}', 'error')
    
    professionals = Professional.query.filter_by(is_active=True).all()
    
    # Identify professionals with active tasks
    active_statuses = [Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS]
    busy_professional_ids = {
        t.assigned_professional_id for t in Ticket.query.filter(
            Ticket.status.in_(active_statuses),
            Ticket.assigned_professional_id.isnot(None)
        ).all()
    }
    
    professionals_by_category = {}
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    for prof in professionals:
        cat = prof.category
        if cat not in professionals_by_category:
            professionals_by_category[cat] = {
                'name': category_names.get(cat, cat),
                'professionals': []
            }
        professionals_by_category[cat]['professionals'].append(prof)
    
    return render_template('admin/assign_ticket.html',
                         ticket=ticket,
                         professionals_by_category=professionals_by_category,
                         category_names=category_names,
                         busy_professional_ids=busy_professional_ids)


@admin_bp.route('/api/ticket/<int:ticket_id>/assign', methods=['POST'])
@admin_required
def api_assign_ticket(ticket_id):
    """Assign ticket via API (AJAX)."""
    ticket = Ticket.query.get_or_404(ticket_id)
    data = request.get_json()
    
    professional_id = data.get('professional_id')
    time_limit_hours = data.get('time_limit_hours')
    
    if not professional_id:
        return jsonify({'success': False, 'error': 'Professional ID required'}), 400
    
    if not time_limit_hours or time_limit_hours < 1:
        return jsonify({'success': False, 'error': 'Valid time limit required'}), 400
    
    professional = Professional.query.get(professional_id)
    if not professional or not professional.is_active:
        return jsonify({'success': False, 'error': 'Professional not available'}), 400
    
    # Check if professional already has an active task
    active_task = Ticket.query.filter(
        Ticket.assigned_professional_id == professional_id,
        Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])
    ).first()
    
    if active_task:
        return jsonify({
            'success': False, 
            'error': f'{professional.name} already has an active task (# {active_task.id}). They must complete it before being assigned a new one.'
        }), 400
    
    try:
        ticket.assigned_professional_id = professional_id
        ticket.time_limit_hours = time_limit_hours
        ticket.deadline_datetime = datetime.utcnow() + timedelta(hours=time_limit_hours)
        ticket.status = Ticket.STATUS_ASSIGNED
        db.session.commit()
        
        from .socket_events import notify_professional_assigned
        notify_professional_assigned(ticket, professional)
        
        return jsonify({
            'success': True,
            'message': f'Ticket assigned to {professional.name}',
            'ticket': ticket.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== HELP REQUEST MANAGEMENT ====================

@admin_bp.route('/help-requests')
@admin_required
def help_requests():
    """View all help requests."""
    status_filter = request.args.get('status', 'pending')
    
    help_requests_all = HelpRequest.query.all()
    counts = {
        'pending': sum(1 for r in help_requests_all if r.status == 'pending'),
        'approved': sum(1 for r in help_requests_all if r.status == 'approved'),
        'rejected': sum(1 for r in help_requests_all if r.status == 'rejected'),
        'total': len(help_requests_all)
    }
    
    if status_filter != 'all':
        help_requests_list = [r for r in help_requests_all if r.status == status_filter]
    else:
        help_requests_list = help_requests_all
        
    # Sort by requested_at desc
    help_requests_list.sort(key=lambda x: x.requested_at, reverse=True)
    
    return render_template('admin/help_requests.html',
                         help_requests=help_requests_list,
                         status_filter=status_filter,
                         counts=counts)


@admin_bp.route('/api/help-request/<int:help_request_id>/respond', methods=['POST'])
@admin_required
def respond_to_help_request(help_request_id):
    """Approve or reject a help request (AJAX)."""
    help_request = HelpRequest.query.get_or_404(help_request_id)
    data = request.get_json()
    
    action = data.get('action')
    helper_professional_id = data.get('helper_professional_id')
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    
    if action == 'approve' and not helper_professional_id:
        return jsonify({'success': False, 'error': 'Helper professional required for approval'}), 400
    
    try:
        admin = User.query.get(session['user_id'])
        
        if action == 'approve':
            helper = Professional.query.get(helper_professional_id)
            if not helper or not helper.is_active:
                return jsonify({'success': False, 'error': 'Helper professional not available'}), 400
            
            help_request.status = HelpRequest.STATUS_APPROVED
            help_request.helper_professional_id = helper_professional_id
            help_request.admin_id = admin.id
            help_request.responded_at = datetime.utcnow()
            
            from .socket_events import notify_help_request_approved
            notify_help_request_approved(help_request)
            
        else:
            help_request.status = HelpRequest.STATUS_REJECTED
            help_request.admin_id = admin.id
            help_request.responded_at = datetime.utcnow()
            
            from .socket_events import notify_help_request_rejected
            notify_help_request_rejected(help_request)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Help request {action}d successfully',
            'help_request': help_request.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== CHAT ENDPOINTS ====================

@admin_bp.route('/chat')
@admin_required
def chat():
    """Admin chat interface."""
    professional_id = request.args.get('professional_id', type=int)
    return render_template('admin/chat.html', professional_id=professional_id)


@admin_bp.route('/api/chat/professionals')
@admin_required
def get_professionals_for_chat():
    """Get list of professionals for admin to chat with."""
    professionals = Professional.query.filter_by(is_active=True).all()
    
    result = []
    for prof in professionals:
        unread_count = ChatMessage.query.filter_by(
            sender_type=ChatMessage.SENDER_TYPE_PROFESSIONAL,
            sender_id=prof.id,
            receiver_type=ChatMessage.SENDER_TYPE_ADMIN,
            is_read=False
        ).count()
        
        result.append({
            'id': prof.id,
            'name': prof.name,
            'category': prof.category,
            'unread_count': unread_count
        })
    
    return jsonify({'success': True, 'professionals': result})


@admin_bp.route('/api/chat/history/<int:professional_id>')
@admin_required
def get_chat_history_with_professional(professional_id):
    """Get chat history with a specific professional."""
    admin = User.query.get(session['user_id'])
    professional = Professional.query.get_or_404(professional_id)
    
    messages = ChatMessage.query.filter(
        (
            ((ChatMessage.sender_type == ChatMessage.SENDER_TYPE_ADMIN) & (ChatMessage.sender_id == admin.id)) |
            ((ChatMessage.receiver_type == ChatMessage.SENDER_TYPE_ADMIN) & (ChatMessage.receiver_id == admin.id))
        ) &
        (
            ((ChatMessage.sender_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & (ChatMessage.sender_id == professional.id)) |
            ((ChatMessage.receiver_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & (ChatMessage.receiver_id == professional.id))
        )
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    # Mark messages from professional to admin as read
    for msg in messages:
        if msg.receiver_type == ChatMessage.SENDER_TYPE_ADMIN:
            msg.is_read = True
    db.session.commit()
    
    return jsonify({
        'success': True,
        'messages': [msg.to_dict() for msg in messages],
        'professional': professional.to_dict()
    })


@admin_bp.route('/api/chat/send', methods=['POST'])
@admin_required
def admin_send_chat_message():
    """Admin sends a chat message to professional."""
    admin = User.query.get(session['user_id'])
    data = request.get_json()
    
    professional_id = data.get('professional_id')
    message_text = data.get('message', '').strip()
    
    if not professional_id or not message_text:
        return jsonify({'success': False, 'error': 'Professional ID and message required'}), 400
    
    professional = Professional.query.get(professional_id)
    if not professional:
        return jsonify({'success': False, 'error': 'Professional not found'}), 404
    
    try:
        chat_message = ChatMessage(
            sender_type=ChatMessage.SENDER_TYPE_ADMIN,
            sender_id=admin.id,
            receiver_type=ChatMessage.SENDER_TYPE_PROFESSIONAL,
            receiver_id=professional_id,
            message=message_text
        )
        db.session.add(chat_message)
        db.session.commit()
        
        from .socket_events import emit_chat_message
        emit_chat_message(chat_message)
        
        return jsonify({
            'success': True,
            'message': chat_message.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/chat/reset/<int:prof_id>', methods=['POST'])
@admin_required
def reset_professional_chat(prof_id):
    """Reset chat history for a specific professional."""
    from .models import User
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    
    if not user or not user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        from .models import ChatMessage
        ChatMessage.query.filter(
            ((ChatMessage.sender_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & (ChatMessage.sender_id == prof_id)) |
            ((ChatMessage.receiver_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & (ChatMessage.receiver_id == prof_id))
        ).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
