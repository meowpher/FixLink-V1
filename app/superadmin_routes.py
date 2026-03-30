"""
Super Admin Routes - Developer Dashboard for managing admins and professionals
Accessible only with hardcoded credentials:
Email: taha.piplodwala@mitwpu.edu.in
Password: Taha10vesgono!
"""
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User, Professional

superadmin_bp = Blueprint('superadmin', __name__)

# Hardcoded super admin credentials
SUPER_ADMIN_EMAIL = 'taha.piplodwala@mitwpu.edu.in'
SUPER_ADMIN_PASSWORD_HASH = generate_password_hash('Taha10vesgono!')

def super_admin_required(f):
    """Decorator to require super admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_super_admin'):
            return redirect(url_for('superadmin.login'))
        return f(*args, **kwargs)
    return decorated_function


@superadmin_bp.route('/developer/login', methods=['GET', 'POST'])
def login():
    """Super admin login page."""
    if session.get('is_super_admin'):
        return redirect(url_for('superadmin.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if email == SUPER_ADMIN_EMAIL and check_password_hash(SUPER_ADMIN_PASSWORD_HASH, password):
            session['is_super_admin'] = True
            session['super_admin_email'] = email
            flash('Welcome, Developer!', 'success')
            return redirect(url_for('superadmin.dashboard'))
        else:
            flash('Invalid credentials.', 'error')
    
    return render_template('superadmin/login.html')


@superadmin_bp.route('/developer/logout')
def logout():
    """Logout super admin."""
    session.pop('is_super_admin', None)
    session.pop('super_admin_email', None)
    flash('Logged out.', 'info')
    return redirect(url_for('superadmin.login'))


@superadmin_bp.route('/developer')
@super_admin_required
def dashboard():
    """Developer dashboard - manage admins and professionals."""
    # Get counts
    admin_count = User.query.filter_by(is_admin=True).count()
    professional_count = Professional.query.filter_by(is_active=True).count()
    
    return render_template('superadmin/dashboard.html',
                         admin_count=admin_count,
                         professional_count=professional_count)


# ==================== ADD NEW ADMIN ====================

@superadmin_bp.route('/developer/add-admin', methods=['GET', 'POST'])
@super_admin_required
def add_admin():
    """Add a new admin user."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        # Validation
        errors = []
        if not name:
            errors.append('Name is required')
        if not email:
            errors.append('Email is required')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters')
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('superadmin/add_admin.html', form_data=request.form)
        
        try:
            admin_user = User(
                name=name,
                email=email,
                is_admin=True,
                is_verified=True
            )
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            
            flash(f'Admin {name} created successfully!', 'success')
            return redirect(url_for('superadmin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating admin: {str(e)}', 'error')
    
    return render_template('superadmin/add_admin.html')


# ==================== ADD NEW PROFESSIONAL (Job Certified) ====================

@superadmin_bp.route('/developer/add-professional', methods=['GET', 'POST'])
@super_admin_required
def add_professional():
    """Add a new Job Certified Professional."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower() or None
        phone = request.form.get('phone', '').strip() or None
        category = request.form.get('category', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validation
        errors = []
        if not name:
            errors.append('Name is required')
        if not username:
            errors.append('Username is required')
        if not phone and not email:
            errors.append('Either phone or email is required')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters')
        if category not in Professional.CATEGORIES:
            errors.append('Invalid category')
        
        # Check if username exists
        if Professional.query.filter_by(username=username).first():
            errors.append('Username already exists')
        
        # Check if phone exists
        if phone and Professional.query.filter_by(phone=phone).first():
            errors.append('Phone number already registered')
        
        # Check if email exists
        if email and Professional.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('superadmin/add_professional.html', 
                                 categories=Professional.CATEGORIES,
                                 form_data=request.form)
        
        try:
            professional = Professional(
                username=username,
                name=name,
                email=email,
                phone=phone,
                category=category,
                is_active=True
            )
            professional.set_password(password)
            db.session.add(professional)
            db.session.commit()
            
            flash(f'Job Certified Professional {name} created successfully!', 'success')
            return redirect(url_for('superadmin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating professional: {str(e)}', 'error')
    
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    return render_template('superadmin/add_professional.html',
                         categories=Professional.CATEGORIES,
                         category_names=category_names)


# ==================== LIST AND MANAGE ====================

@superadmin_bp.route('/developer/admins')
@super_admin_required
def list_admins():
    """List all admin users."""
    admins = User.query.filter_by(is_admin=True).all()
    return render_template('superadmin/list_admins.html', admins=admins)


@superadmin_bp.route('/developer/professionals')
@super_admin_required
def list_professionals():
    """List all professionals."""
    professionals = Professional.query.order_by(Professional.created_at.desc()).all()
    
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    return render_template('superadmin/list_professionals.html', 
                         professionals=professionals,
                         categories=Professional.CATEGORIES,
                         category_names=category_names)


# ==================== DELETE ENDPOINTS ====================

@superadmin_bp.route('/developer/api/admin/<int:admin_id>/delete', methods=['POST'])
@super_admin_required
def delete_admin(admin_id):
    """Delete an admin user."""
    admin = User.query.get_or_404(admin_id)
    
    if admin.email == SUPER_ADMIN_EMAIL:
        return jsonify({'success': False, 'error': 'Cannot delete the super admin'}), 403
    
    try:
        db.session.delete(admin)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@superadmin_bp.route('/developer/api/professional/<int:prof_id>/delete', methods=['POST'])
@super_admin_required
def delete_professional(prof_id):
    """Delete a professional."""
    professional = Professional.query.get_or_404(prof_id)
    
    # Check if professional has assigned tickets
    from .models import Ticket
    assigned_tickets = Ticket.query.filter_by(
        assigned_professional_id=prof_id
    ).filter(
        Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])
    ).count()
    
    if assigned_tickets > 0:
        return jsonify({
            'success': False, 
            'error': f'Cannot delete professional with {assigned_tickets} active tasks'
        }), 400
    
    try:
        db.session.delete(professional)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@superadmin_bp.route('/developer/api/professional/<int:prof_id>/toggle-status', methods=['POST'])
@super_admin_required
def toggle_professional_status(prof_id):
    """Toggle professional active status."""
    professional = Professional.query.get_or_404(prof_id)
    
    try:
        professional.is_active = not professional.is_active
        db.session.commit()
        return jsonify({
            'success': True, 
            'is_active': professional.is_active
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@superadmin_bp.route('/developer/api/professional/<int:prof_id>/edit', methods=['POST'])
@super_admin_required
def edit_professional(prof_id):
    """Edit professional details via API."""
    professional = Professional.query.get_or_404(prof_id)
    data = request.get_json()
    
    # Get new values
    name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    phone = data.get('phone', '').strip() or None
    email = data.get('email', '').strip().lower() or None
    category = data.get('category', '').strip()
    password = data.get('password', '').strip()
    
    # Validation
    errors = []
    if not name:
        errors.append('Name is required')
    if not username:
        errors.append('Username is required')
    if category not in Professional.CATEGORIES:
        errors.append('Invalid category')
    
    # Check if username changed and already exists
    if username != professional.username:
        existing = Professional.query.filter_by(username=username).first()
        if existing:
            errors.append('Username already exists')
    
    # Check if phone changed and already exists
    if phone and phone != professional.phone:
        existing = Professional.query.filter_by(phone=phone).first()
        if existing:
            errors.append('Phone number already registered')
    
    # Check if email changed and already exists
    if email and email != professional.email:
        existing = Professional.query.filter_by(email=email).first()
        if existing:
            errors.append('Email already registered')
    
    if errors:
        return jsonify({'success': False, 'error': '; '.join(errors)}), 400
    
    try:
        # Update fields
        professional.name = name
        professional.username = username
        professional.phone = phone
        professional.email = email
        professional.category = category
        
        # Update password if provided
        if password:
            professional.set_password(password)
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Professional updated successfully',
            'professional': professional.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
