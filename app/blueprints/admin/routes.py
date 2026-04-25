"""
Admin Routes Blueprint - Maintenance Dashboard
"""
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from sqlalchemy import or_, func, case
from ... import db
from ...models import Building, Floor, Room, Asset, Ticket, User, Professional, HelpRequest, ChatMessage
from ...utils import send_ticket_email
from ...decorators import admin_required
from ...analytics import get_technician_efficiency, get_system_trends, get_critical_assets
from ...api_utils import handle_api_errors, api_response

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard - view tickets and statistics."""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    floor_filter = request.args.get('floor', 'all')
    category_filter = request.args.get('category', 'all')
    
    # Base query
    query = Ticket.query
    
    if status_filter != 'all':
        if status_filter == 'open':
            query = query.filter(Ticket.status.in_([Ticket.STATUS_OPEN, Ticket.STATUS_CANCELLED]))
        else:
            query = query.filter(Ticket.status == status_filter)
    
    if floor_filter != 'all':
        query = query.join(Room).filter(Room.floor_id == int(floor_filter))
        
    if category_filter != 'all':
        # Map frontend category groups to specific issue types
        if category_filter == 'electrician':
            query = query.filter(Ticket.issue_type.in_(['electrical', 'ac', 'lighting', 'lift_breakdown', 'light_broken']))
        elif category_filter == 'plumber':
            query = query.filter(Ticket.issue_type == 'plumbing')
        elif category_filter == 'it_technician':
            query = query.filter(Ticket.issue_type.in_(['projector', 'computer']))
        elif category_filter == 'carpenter':
            query = query.filter(Ticket.issue_type.in_(['furniture', 'door_error']))
        elif category_filter == 'other':
            query = query.filter(Ticket.issue_type.in_(['cleaning', 'other']))
    
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
    
    # Unified categories for the filter dropdown
    categories = [
        {'id': 'electrician', 'name': 'Electrical / AC / Lifts'},
        {'id': 'plumber', 'name': 'Plumbing'},
        {'id': 'it_technician', 'name': 'IT / Computer / AV'},
        {'id': 'carpenter', 'name': 'Furniture / Doors'},
        {'id': 'other', 'name': 'Others'}
    ]
    
    return render_template('admin.html',
                         tickets=tickets,
                         stats=stats,
                         floors=floors,
                         categories=categories,
                         status_filter=status_filter,
                         floor_filter=floor_filter,
                         category_filter=category_filter)


@admin_bp.route('/map')
@admin_required
def status_map():
    """Visual status map showing all floors with room status - Optimized."""
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
            selected_floor = next((f for f in floors if f.level == 4), floors[0])
        
        if selected_floor:
            from sqlalchemy.orm import joinedload
            rooms = Room.query.options(
                joinedload(Room.tickets),
                joinedload(Room.assets)
            ).filter_by(floor_id=selected_floor.id).all()
    
    return render_template('status_map.html',
                         floors=floors,
                         selected_floor=selected_floor,
                         rooms=rooms)


@admin_bp.route('/history')
@admin_required
def history():
    """Admin history page - view fixed tickets with search filtering."""
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    # Base query for all fixed tickets
    from sqlalchemy.orm import joinedload
    query = Ticket.query.options(joinedload(Ticket.room).joinedload(Room.floor)).filter_by(status=Ticket.STATUS_FIXED)
    
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            or_(
                Ticket.reporter_name.ilike(search_filter),
                Ticket.prn.ilike(search_filter),
                Ticket.reporter_email.ilike(search_filter)
            )
        )
    
    # Order by fixed date descending and paginate
    pagination = query.order_by(Ticket.fixed_at.desc(), Ticket.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    tickets = pagination.items
    
    return render_template('admin_history.html', 
                          tickets=tickets, 
                          pagination=pagination,
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


@admin_bp.route('/analytics')
@admin_required
def analytics():
    """Admin analytics and insights dashboard with dynamic filtering."""
    # Get filters from request
    period = request.args.get('period', 'monthly')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Base Filters
    query = Ticket.query
    
    # 1. Date Range Handling
    now = datetime.utcnow()
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Ticket.created_at.between(start_date, end_date))
        except ValueError:
            pass # Fallback to default if invalid dates
    elif period == 'daily':
        # Default to last 14 days for daily
        start_date = now - timedelta(days=14)
        query = query.filter(Ticket.created_at >= start_date)
    elif period == 'weekly':
        # Default to last 12 weeks
        start_date = now - timedelta(weeks=12)
        query = query.filter(Ticket.created_at >= start_date)
    else: # Default monthly
        start_date = now - timedelta(days=180)
        query = query.filter(Ticket.created_at >= start_date)

    # 2. Total/Fixed Stats (Respecting filters)
    total_tickets = query.count()
    fixed_tickets_count = query.filter(Ticket.status == Ticket.STATUS_FIXED).count()
    
    # 3. Tickets by Category (Respecting filters)
    raw_category_counts = db.session.query(
        Ticket.issue_type, func.count(Ticket.id)
    ).filter(Ticket.id.in_(db.session.query(Ticket.id).filter(Ticket.created_at >= start_date))).group_by(Ticket.issue_type).all()
    
    # Re-use your consolidated grouping logic
    category_map = {
        'electrical': 'Electrical & Utilities', 'ac': 'Electrical & Utilities', 
        'lighting': 'Electrical & Utilities', 'light_broken': 'Electrical & Utilities',
        'lift_breakdown': 'Electrical & Utilities', 'lift_not_working': 'Electrical & Utilities',
        'projector': 'IT & AV Systems', 'computer': 'IT & AV Systems',
        'plumbing': 'Plumbing', 'furniture': 'Furniture & Carpentry', 
        'chairs': 'Furniture & Carpentry', 'door_error': 'Furniture & Carpentry',
    }
    
    consolidated_data = {}
    for issue_type, count in raw_category_counts:
        group_name = category_map.get(issue_type, 'Other')
        consolidated_data[group_name] = consolidated_data.get(group_name, 0) + count
    
    # 4. Success Rate
    success_rate = round((fixed_tickets_count / total_tickets * 100), 1) if total_tickets > 0 else 0
    
    # 5. Average Resolution Time (Filtered)
    avg_res_time = 0
    fixed_tickets_q = query.filter(
        Ticket.status == Ticket.STATUS_FIXED,
        Ticket.fixed_at.isnot(None)
    ).all()
    
    if fixed_tickets_q:
        durations = [(t.fixed_at - t.created_at).total_seconds() for t in fixed_tickets_q]
        avg_res_time = round(sum(durations) / (3600 * len(durations)), 1) # in hours

    # 6. Trend Grouping Based on Period
    if period == 'daily':
        fmt = 'YYYY-MM-DD'
    elif period == 'weekly':
        fmt = 'IYYY-"W"IW'
    else:
        fmt = 'YYYY-MM'
        
    trend_query = db.session.query(
        func.to_char(Ticket.created_at, fmt).label('label'),
        func.count(Ticket.id)
    ).filter(Ticket.id.in_(db.session.query(Ticket.id).filter(Ticket.created_at >= (start_date if 'start_date' in locals() else now - timedelta(days=180))))).group_by('label').order_by('label').all()
    
    trend_data = [list(row) for row in trend_query]

    # Current Risks (Always current)
    critical_assets = get_critical_assets(5)

    return render_template('admin_analytics.html',
                          total_tickets=total_tickets,
                          fixed_count=fixed_tickets_count,
                          category_data=consolidated_data,
                          avg_res_time=avg_res_time,
                          success_rate=success_rate,
                          monthly_trend=trend_data,
                          period=period,
                          start_date=start_date_str,
                          end_date=end_date_str,
                          critical_assets=critical_assets)


@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
@handle_api_errors
def edit_user(user_id):
    """Edit user details (AJAX)."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    if email != user.email:
        if User.query.filter_by(email=email).first():
            return api_response(success=False, error="Email already registered.", status=400)
            
    user.name = data.get('name', '').strip()
    user.email = email
    user.prn = data.get('prn', '').strip()
    user.is_admin = data.get('role') == 'admin'
    
    password = data.get('password')
    if password:
        user.set_password(password)
        
    db.session.commit()
    return jsonify({
        'success': True,
        'message': "User updated successfully"
    })


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
@handle_api_errors
def delete_user(user_id):
    """Delete a user (AJAX)."""
    if user_id == session.get('user_id'):
        return api_response(success=False, error="Cannot delete yourself.", status=400)
        
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': "User deleted successfully"
    })


@admin_bp.route('/users/<int:user_id>/verify', methods=['POST'])
@admin_required
@handle_api_errors
def verify_user_manual(user_id):
    """Manually verify a user (AJAX)."""
    user = User.query.get_or_404(user_id)
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    return jsonify({
        'success': True,
        'message': "User verified successfully"
    })


@admin_bp.route('/tickets/<int:ticket_id>/update-status', methods=['POST'])
@admin_required
@handle_api_errors
def update_ticket_status(ticket_id):
    """Update ticket status (AJAX endpoint)."""
    ticket = Ticket.query.get_or_404(ticket_id)
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in Ticket.STATUS_CHOICES:
        return api_response(success=False, error="Invalid status", status=400)
    
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
    
    # Invalidate map cache for affected floor
    if ticket.room_id:
        room = Room.query.get(ticket.room_id)
        if room:
            from ...cache import invalidate_floor_cache
            invalidate_floor_cache(room.floor_id)
    
    # Trigger EmailJS notification for ticket update
    send_ticket_email(ticket, action=new_status)
    
    return jsonify({
        'success': True,
        'message': f"Ticket #{ticket.id} marked as {new_status}",
        'ticket_id': ticket.id,
        'status': ticket.status
    })


@admin_bp.route('/ticket/<int:ticket_id>')
@admin_required
@handle_api_errors
def get_ticket_detail(ticket_id):
    """Get ticket details for modal (AJAX)."""
    ticket = Ticket.query.get_or_404(ticket_id)
    return jsonify({'success': True, 'ticket': ticket.to_dict()})


@admin_bp.route('/floor-data/<int:floor_id>')
@admin_required
@handle_api_errors
def get_floor_data(floor_id):
    """Get floor data with room statuses for map (AJAX) - Optimized."""
    from ...cache import cache
    
    cache_key = f'admin_floor_{floor_id}'
    cached = cache.get(cache_key)
    if cached:
        return jsonify({
            'success': True,
            **cached
        })
    
    floor = Floor.query.get_or_404(floor_id)
    
    from sqlalchemy.orm import joinedload
    rooms = Room.query.options(
        joinedload(Room.tickets),
        joinedload(Room.assets)
    ).filter_by(floor_id=floor_id).all()
    
    result = {
        'floor': floor.to_dict(),
        'rooms': [room.to_map_dict() for room in rooms]
    }
    
    cache.set(cache_key, result, timeout=3600)  # 60 minutes
    return jsonify({
        'success': True,
        **result
    })


@admin_bp.route('/api/room-status/<room_number>')
@admin_required
@handle_api_errors
def api_room_status(room_number):
    """Detailed room status for the interactive map (AJAX)."""
    room = Room.query.filter(Room.number.ilike(room_number)).first_or_404()
    
    # Get active ticket (open, assigned, or in-progress)
    active_ticket = Ticket.query.filter(
        Ticket.room_id == room.id,
        Ticket.status.in_([Ticket.STATUS_OPEN, Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])
    ).order_by(Ticket.created_at.desc()).first()
    
    # Get all active professionals for assignment
    all_profs = Professional.query.filter_by(is_active=True).all()
    profs_by_category = {}
    
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    for p in all_profs:
        cat_name = category_names.get(p.category, p.category.title())
        if cat_name not in profs_by_category:
            profs_by_category[cat_name] = []
        profs_by_category[cat_name].append({
            'id': p.id,
            'name': p.name
        })
    
    return jsonify({
        'success': True,
        'room': room.to_dict(),
        'status': room.status,
        'active_ticket': active_ticket.to_dict() if active_ticket else None,
        'professionals': profs_by_category
    })


@admin_bp.route('/api/ticket/<int:ticket_id>/assign', methods=['POST'])
@admin_required
@handle_api_errors
def api_assign_ticket(ticket_id):
    """Assign a ticket to a professional via AJAX."""
    from datetime import datetime, timedelta
    from ...cache import invalidate_floor_cache
    
    ticket = Ticket.query.get_or_404(ticket_id)
    data = request.get_json()
    
    professional_id = data.get('professional_id')
    time_limit_hours = int(data.get('time_limit_hours', 2))
    
    if not professional_id:
        return api_response(success=False, error="Please select a professional", status=400)
        
    professional = Professional.query.get(professional_id)
    if not professional or not professional.is_active:
        return api_response(success=False, error="Selected professional is not available", status=400)
        
    # Check if professional already has an active task
    active_task = Ticket.query.filter(
        Ticket.assigned_professional_id == professional_id,
        Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])
    ).first()
    
    if active_task:
        return api_response(success=False, error=f"{professional.name} already has an active task (# {active_task.id}).", status=400)

    ticket.assigned_professional_id = professional_id
    ticket.time_limit_hours = time_limit_hours
    ticket.deadline_datetime = datetime.utcnow() + timedelta(hours=time_limit_hours)
    ticket.status = Ticket.STATUS_ASSIGNED
    
    db.session.commit()
    
    # Invalidate cache for the floor
    if ticket.room_id:
        invalidate_floor_cache(ticket.room.floor_id)
        
    return jsonify({
        'success': True,
        'message': "Technician assigned successfully"
    })


@admin_bp.route('/tickets/<int:ticket_id>/delete', methods=['POST'])
@admin_required
@handle_api_errors
def delete_ticket(ticket_id):
    """Delete a ticket (AJAX endpoint)."""
    ticket = Ticket.query.get_or_404(ticket_id)
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
        'message': f"Ticket #{ticket.id} deleted successfully"
    })


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
@handle_api_errors
def edit_professional(professional_id):
    """Edit professional details (AJAX)."""
    professional = Professional.query.get_or_404(professional_id)
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    if email != professional.email:
        if Professional.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'error': "Email already registered."
            }), 400
    
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
    return jsonify({
        'success': True,
        'message': "Professional updated successfully"
    })


@admin_bp.route('/professionals/<int:professional_id>/delete', methods=['POST'])
@admin_required
@handle_api_errors
def delete_professional(professional_id):
    """Delete a professional (AJAX)."""
    professional = Professional.query.get_or_404(professional_id)
    
    assigned_tickets = Ticket.query.filter_by(
        assigned_professional_id=professional_id
    ).filter(
        Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])
    ).count()
    
    if assigned_tickets > 0:
        return api_response(
            success=False, 
            error=f"Cannot delete professional with {assigned_tickets} active tasks. Reassign tasks first.", 
            status=400
        )
    
    db.session.delete(professional)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': "Professional deleted successfully"
    })


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
            
            from ...realtime import notify_professional_assigned
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




# ==================== HELP REQUEST MANAGEMENT ====================

@admin_bp.route('/help-requests')
@admin_required
def help_requests():
    """View all help requests."""
    status_filter = request.args.get('status', 'pending')
    
    # Use efficient DB-level aggregation for counts
    counts = {
        'pending': HelpRequest.query.filter_by(status='pending').count(),
        'approved': HelpRequest.query.filter_by(status='approved').count(),
        'rejected': HelpRequest.query.filter_by(status='rejected').count(),
        'total': HelpRequest.query.count()
    }
    
    # Efficient DB-level filtering and sorting
    query = HelpRequest.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    help_requests_list = query.order_by(HelpRequest.requested_at.desc()).all()
    
    return render_template('admin/help_requests.html',
                         help_requests=help_requests_list,
                         status_filter=status_filter,
                         counts=counts)


@admin_bp.route('/api/help-request/<int:help_request_id>/respond', methods=['POST'])
@admin_required
@handle_api_errors
def respond_to_help_request(help_request_id):
    """Approve or reject a help request (AJAX)."""
    help_request = HelpRequest.query.get_or_404(help_request_id)
    data = request.get_json()
    
    action = data.get('action')
    helper_professional_id = data.get('helper_professional_id')
    
    if action not in ['approve', 'reject']:
        return jsonify({
            'success': False,
            'error': "Invalid action"
        }), 400
    
    if action == 'approve' and not helper_professional_id:
        return jsonify({
            'success': False,
            'error': "Helper professional required for approval"
        }), 400
    
    admin = User.query.get(session['user_id'])
    
    if action == 'approve':
        helper = Professional.query.get(helper_professional_id)
        if not helper or not helper.is_active:
            return jsonify({
                'success': False,
                'error': "Helper professional not available"
            }), 400
        
        help_request.status = HelpRequest.STATUS_APPROVED
        help_request.helper_professional_id = helper_professional_id
        help_request.admin_id = admin.id
        help_request.responded_at = datetime.utcnow()
        
        from ...realtime import notify_help_request_approved
        notify_help_request_approved(help_request)
        
    else:
        help_request.status = HelpRequest.STATUS_REJECTED
        help_request.admin_id = admin.id
        help_request.responded_at = datetime.utcnow()
        
        from ...realtime import notify_help_request_rejected
        notify_help_request_rejected(help_request)
    
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f"Help request {action}d successfully"
    })


# ==================== ANALYTICS & REPORTS ====================


# Merged analytics into single route /analytics (Line 223)

@admin_bp.route('/reports/export/<string:fmt>')
@admin_required
def export_report(fmt):
    """Export maintenance data as PDF or CSV."""
    import pandas as pd
    from flask import make_response
    from io import BytesIO, StringIO
    
    # Fetch filters for report
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    query = Ticket.query
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Ticket.created_at.between(start_date, end_date))
        except ValueError:
            pass
            
    tickets = query.order_by(Ticket.created_at.desc()).all()
    data = [t.to_dict() for t in tickets]
    if not data:
        flash('No data available for export.', 'info')
        return redirect(url_for('admin.dashboard'))
        
    df = pd.DataFrame(data)
    
    # Format dates for export
    date_cols = ['created_at', 'updated_at', 'job_started_at', 'job_completed_at', 'fixed_at', 'deadline_datetime']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')

    if fmt == 'csv':
        output = StringIO()
        df.to_csv(output, index=False)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=fixlink_report_{datetime.now().strftime('%Y%m%d')}.csv"
        response.headers["Content-type"] = "text/csv"
        return response
    
    elif fmt == 'pdf':
        from fpdf import FPDF
        import os
        from flask import current_app
        
        # Calculate Advanced Analytics for the report
        tech_stats = get_technician_efficiency()
        critical_assets = get_critical_assets(5)
        
        # Global branding colors
        BRAND_BLUE = (11, 77, 140)
        TEXT_DARK = (40, 40, 40)
        TEXT_MUTED = (100, 100, 100)
        SUCCESS_GREEN = (40, 167, 69)
        DANGER_RED = (220, 53, 69)
        
        class PDF(FPDF):
            def header(self):
                # Branding Logo
                logo_path = os.path.join(current_app.root_path, 'static', 'images', 'logo-lm.png')
                if os.path.exists(logo_path):
                    self.image(logo_path, 10, 8, 33)
                
                self.set_font('helvetica', 'B', 15)
                self.set_text_color(*BRAND_BLUE)
                self.cell(80) # Move to the right
                self.cell(110, 10, 'FixLink: Maintenance Performance Report', border=0, align='R')
                self.ln(5)
                self.cell(80)
                self.set_font('helvetica', '', 9)
                self.set_text_color(*TEXT_MUTED)
                self.cell(110, 10, 'MIT-WPU Smart-Room Maintenance Ecosystem', border=0, align='R')
                self.ln(15)
                # Line break
                self.set_draw_color(*BRAND_BLUE)
                self.set_line_width(0.5)
                self.line(10, 32, 200, 32)
                self.ln(10)

            def footer(self):
                self.set_y(-15)
                self.set_font('helvetica', 'I', 8)
                self.set_text_color(*TEXT_MUTED)
                self.cell(0, 10, f'MIT-WPU FixLink Confidential | Page {self.page_no()}/{{nb}}', align='C')
                self.cell(0, 10, f'Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', align='R')

            def chapter_title(self, label):
                self.set_font('helvetica', 'B', 12)
                self.set_text_color(*BRAND_BLUE)
                self.set_fill_color(240, 245, 255)
                self.cell(0, 10, f'  {label}', ln=True, fill=True)
                self.ln(4)

        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # --- SECTION 1: EXECUTIVE SUMMARY ---
        pdf.chapter_title('Executive Summary')
        
        # KPI Boxes
        total_count = len(df)
        fixed_count = len(df[df['status'] == 'fixed'])
        success_rate = round((fixed_count / total_count * 100), 1) if total_count > 0 else 0
        
        pdf.set_font('helvetica', 'B', 10)
        pdf.set_text_color(*TEXT_DARK)
        
        # Stats Row
        col_width = (pdf.w - 20) / 3
        pdf.cell(col_width, 10, 'Total Requests', align='C')
        pdf.cell(col_width, 10, 'Completion Rate', align='C')
        pdf.cell(col_width, 10, 'Critical Assets', align='C')
        pdf.ln(8)
        
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(*BRAND_BLUE)
        pdf.cell(col_width, 10, str(total_count), align='C')
        pdf.cell(col_width, 10, f'{success_rate}%', align='C')
        pdf.cell(col_width, 10, str(len(critical_assets)), align='C')
        pdf.ln(15)
        
        # --- SECTION 2: TECHNICIAN PERFORMANCE ---
        if tech_stats:
            pdf.chapter_title('Technician Efficiency Overview')
            pdf.set_font('helvetica', 'B', 9)
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(60, 8, ' Professional Name', border=1, fill=True)
            pdf.cell(40, 8, ' Category', border=1, fill=True)
            pdf.cell(30, 8, ' Closed Jobs', border=1, fill=True, align='C')
            pdf.cell(60, 8, ' Avg. Resolution Time', border=1, fill=True, align='C')
            pdf.ln()
            
            pdf.set_font('helvetica', '', 9)
            pdf.set_text_color(*TEXT_DARK)
            for tech in tech_stats[:5]: # Top 5
                pdf.cell(60, 8, f" {tech['name']}", border=1)
                pdf.cell(40, 8, f" {tech['category'].title()}", border=1)
                pdf.cell(30, 8, str(tech['fixed_count']), border=1, align='C')
                pdf.cell(60, 8, f"{tech['avg_ttr_hours']} hours", border=1, align='C')
                pdf.ln()
            pdf.ln(10)

        # --- SECTION 3: SERVICE CATEGORY DISTRIBUTION ---
        pdf.chapter_title('Service Category Distribution & Visual Analysis')
        category_map = {
            'electrical': 'Electrical & Utilities', 'ac': 'Electrical & Utilities', 
            'lighting': 'Electrical & Utilities', 'light_broken': 'Electrical & Utilities',
            'lift_breakdown': 'Electrical & Utilities', 'lift_not_working': 'Electrical & Utilities',
            'projector': 'IT & AV Systems', 'computer': 'IT & AV Systems',
            'plumbing': 'Plumbing', 'furniture': 'Furniture & Carpentry', 
            'chairs': 'Furniture & Carpentry', 'door_error': 'Furniture & Carpentry',
        }
        
        consolidated_counts = {}
        for _, row in df.iterrows():
            group_name = category_map.get(row['issue_type'], 'Other')
            consolidated_counts[group_name] = consolidated_counts.get(group_name, 0) + 1
            
        pdf.set_font('helvetica', 'B', 9)
        pdf.set_fill_color(*BRAND_BLUE)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(70, 10, ' Category Group', border=1, fill=True)
        pdf.cell(30, 10, ' Count', border=1, fill=True, align='C')
        pdf.cell(40, 10, ' Distribution', border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_font('helvetica', '', 9)
        pdf.set_text_color(*TEXT_DARK)
        
        # Prepare data for pie chart
        sorted_cats = sorted(consolidated_counts.items(), key=lambda x: x[1], reverse=True)
        labels = [c[0] for c in sorted_cats]
        sizes = [c[1] for c in sorted_cats]
        
        for cat, count in sorted_cats:
            pct = (count / total_count * 100) if total_count > 0 else 0
            pdf.cell(70, 8, f" {cat}", border=1)
            pdf.cell(30, 8, str(count), border=1, align='C')
            pdf.cell(40, 8, f"{round(pct, 1)}%", border=1, align='C')
            pdf.ln()
            
        # Generate Pie Chart using Matplotlib
        import matplotlib.pyplot as plt
        import io
        plt.switch_backend('Agg') # Headless mode
        
        # Consistent color palette matching the dashboard
        colors = ['#0b4d8c', '#ffcc00', '#28a745', '#dc3545', '#17a2b8', '#6610f2', '#fd7e14']
        
        fig, ax = plt.subplots(figsize=(6, 4))
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                       colors=colors[:len(labels)], startangle=140,
                                       textprops={'fontsize': 8})
        plt.setp(autotexts, size=8, weight="bold", color="white")
        ax.axis('equal')
        plt.tight_layout()
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150)
        img_buf.seek(0)
        
        # Insert Chart into PDF (positioned next to/below table)
        pdf.ln(5)
        # Use 140mm width (center it roughly)
        pdf.image(img_buf, x=35, w=140)
        plt.close(fig) # Cleanup
        pdf.ln(10)

        # --- SECTION 4: DETAILED TICKET LOG ---
        pdf.chapter_title('Detailed Maintenance Log')
        
        # Table Header
        pdf.set_font('helvetica', 'B', 9)
        pdf.set_fill_color(*BRAND_BLUE)
        pdf.set_text_color(255, 255, 255)
        
        headers = [('ID', 15), ('Room', 25), ('Status', 30), ('Category', 30), ('Issue Description', 90)]
        for h_text, h_width in headers:
            pdf.cell(h_width, 10, f' {h_text}', border=1, fill=True)
        pdf.ln()
        
        # Table Data
        pdf.set_font('helvetica', '', 8)
        pdf.set_text_color(*TEXT_DARK)
        
        for _, row in df.iterrows():
            # Check for page break
            if pdf.get_y() > 260:
                pdf.add_page()
                # Re-add headers on new page
                pdf.set_font('helvetica', 'B', 9)
                pdf.set_fill_color(*BRAND_BLUE)
                pdf.set_text_color(255, 255, 255)
                for h_text, h_width in headers:
                    pdf.cell(h_width, 10, f' {h_text}', border=1, fill=True)
                pdf.ln()
                pdf.set_font('helvetica', '', 8)
                pdf.set_text_color(*TEXT_DARK)

            # Determine status color
            status = str(row['status']).lower()
            if status == 'fixed':
                pdf.set_text_color(*SUCCESS_GREEN)
            elif status in ['open', 'cancelled']:
                pdf.set_text_color(*DANGER_RED)
            else:
                pdf.set_text_color(*TEXT_DARK)
            
            # Draw row
            h = 8
            pdf.cell(15, h, f" {row['id']}", border=1)
            pdf.set_text_color(*TEXT_DARK) # Reset color for rest of row
            pdf.cell(25, h, f" {row.get('room_number', 'N/A')}", border=1)
            
            # Status badge (using text color)
            if status == 'fixed': pdf.set_text_color(*SUCCESS_GREEN)
            elif status in ['open', 'cancelled']: pdf.set_text_color(*DANGER_RED)
            pdf.cell(30, h, f" {status.upper()}", border=1)
            pdf.set_text_color(*TEXT_DARK)
            
            pdf.cell(30, h, f" {str(row['issue_type']).title()}", border=1)
            
            # Issue description (handles long text)
            issue_text = str(row.get('description', row['issue_type']))
            if len(issue_text) > 55:
                issue_text = issue_text[:52] + "..."
            pdf.cell(90, h, f" {issue_text}", border=1)
            pdf.ln()
            
        # Ensure output is bytes for Flask/Werkzeug response
        pdf_output = pdf.output()
        response = make_response(bytes(pdf_output))
        response.headers["Content-Disposition"] = f"attachment; filename=fixlink_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        response.headers["Content-type"] = "application/pdf"
        return response

    return redirect(url_for('admin.dashboard'))


# ==================== CHAT ENDPOINTS ====================

@admin_bp.route('/chat')
@admin_required
def chat():
    """Admin chat interface."""
    professional_id = request.args.get('professional_id', type=int)
    return render_template('admin/chat.html', professional_id=professional_id)


@admin_bp.route('/api/chat/professionals')
@admin_required
@handle_api_errors
def get_professionals_for_chat():
    """Get list of professionals for admin to chat with."""
    from ...models import ChatMessage
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
    
    return jsonify({
        'success': True,
        'professionals': result
    })


@admin_bp.route('/api/chat/history/<int:professional_id>')
@admin_required
@handle_api_errors
def get_chat_history_with_professional(professional_id):
    """Get chat history with a specific professional."""
    from ...models import ChatMessage
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
@handle_api_errors
def admin_send_chat_message():
    """Admin sends a chat message to professional."""
    from ...models import ChatMessage
    from ...api_utils import validate_json
    
    admin = User.query.get(session['user_id'])
    data, error = validate_json(['professional_id', 'message'])
    if error: return error
    
    professional_id = data.get('professional_id')
    message_text = data.get('message', '').strip()
    
    professional = Professional.query.get(professional_id)
    if not professional:
        return api_response(success=False, error="Professional not found", status=404)
    
    chat_message = ChatMessage(
        sender_type=ChatMessage.SENDER_TYPE_ADMIN,
        sender_id=admin.id,
        receiver_type=ChatMessage.SENDER_TYPE_PROFESSIONAL,
        receiver_id=professional_id,
        message=message_text
    )
    db.session.add(chat_message)
    db.session.commit()
    
    from ...realtime import emit_chat_message
    emit_chat_message(chat_message)
    
    return jsonify({
        'success': True,
        'message': 'Message sent successfully',
        'chat_message': chat_message.to_dict()
    })


@admin_bp.route('/api/chat/reset/<int:prof_id>', methods=['POST'])
@admin_required
@handle_api_errors
def reset_professional_chat(prof_id):
    """Reset chat history for a specific professional."""
    from ...models import ChatMessage
    ChatMessage.query.filter(
        ((ChatMessage.sender_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & (ChatMessage.sender_id == prof_id)) |
        ((ChatMessage.receiver_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & (ChatMessage.receiver_id == prof_id))
    ).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': "Chat history reset successfully"
    })


@admin_bp.route('/timetable', methods=['GET', 'POST'])
@admin_required
def timetable():
    """Manage weekly timetable."""
    from ...models import Timetable, Room, User
    from datetime import time
    
    if request.method == 'POST':
        room_id = request.form.get('room_id')
        faculty_id = request.form.get('faculty_id')
        subject = request.form.get('subject')
        day_of_week = int(request.form.get('day_of_week', 0))
        start_hour = int(request.form.get('start_hour', 8))
        duration = int(request.form.get('duration', 1))
        
        if not all([room_id, faculty_id, subject]):
            flash('All fields are required.', 'error')
        else:
            try:
                # Calculate end hour and cap it at 23:59
                end_hour = start_hour + duration
                new_start = time(start_hour, 0)
                
                if end_hour >= 24:
                    new_end = time(23, 59, 59)
                else:
                    new_end = time(end_hour, 0)
                
                conflicts = Timetable.query.filter_by(room_id=room_id, day_of_week=day_of_week).all()
                has_conflict = False
                for tt in conflicts:
                    # Overlap if: new_start < tt.end_time AND tt.start_time < new_end
                    if new_start < tt.end_time and tt.start_time < new_end:
                        has_conflict = True
                        break
                
                if has_conflict:
                    flash('This room is already booked for the selected time slot.', 'error')
                else:
                    tt = Timetable(
                        room_id=room_id,
                        faculty_id=faculty_id,
                        subject=subject,
                        day_of_week=day_of_week,
                        start_time=new_start,
                        end_time=new_end
                    )
                    db.session.add(tt)
                    db.session.commit()
                    flash('Timetable entry added successfully!', 'success')
                    return redirect(url_for('admin.timetable'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding timetable: {str(e)}', 'error')

    # GET: Fetch data for the form and list
    rooms = Room.query.filter(Room.room_type.in_(['class', 'lab'])).order_by(Room.number).all()
    faculty = User.query.filter_by(role=User.ROLE_FACULTY).order_by(User.name).all()
    
    # Filter by room or faculty if provided
    filter_room = request.args.get('room_id')
    filter_faculty = request.args.get('faculty_id')
    
    query = Timetable.query
    if filter_room:
        query = query.filter_by(room_id=filter_room)
    if filter_faculty:
        query = query.filter_by(faculty_id=filter_faculty)
        
    timetables = query.order_by(Timetable.day_of_week, Timetable.start_time).all()
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    return render_template('admin/timetable.html',
                         rooms=rooms,
                         faculty=faculty,
                         timetables=timetables,
                         days=days,
                         filter_room=filter_room,
                         filter_faculty=filter_faculty)


@admin_bp.route('/timetable/<int:tt_id>/delete', methods=['POST'])
@admin_required
def delete_timetable(tt_id):
    """Delete a timetable entry."""
    from ...models import Timetable
    tt = Timetable.query.get_or_404(tt_id)
    db.session.delete(tt)
    db.session.commit()
    flash('Timetable entry removed.', 'success')
    return redirect(url_for('admin.timetable'))
