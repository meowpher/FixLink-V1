"""
Centralized Authentication Decorators for FixLink.
Provides wraps for Admin, Professional, User, and SuperAdmin access control.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify

def login_required(f):
    """Decorator to require any valid login (User, Admin, or Professional)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session and 'professional_id' not in session:
            # Handle AJAX or JSON requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'errors': ['Authentication required. Please log in.']}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            # Handle AJAX requests by returning 401 JSON instead of redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': ['Admin access required. Please log in again.']}), 401
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def user_login_required(f):
    """Decorator to require user login (reporter or admin)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Handle AJAX requests by returning 401 JSON instead of redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': ['Session expired. Please log in again.']}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def faculty_login_required(f):
    """Decorator to require faculty login (or admin for testing)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from .models import User
        if 'user_id' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': ['Session expired. Please log in again.']}), 401
            return redirect(url_for('auth.login'))
            
        user = User.query.get(session['user_id'])
        if not user or (user.role != User.ROLE_FACULTY and not user.is_admin):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': ['Faculty access required.']}), 403
            flash('Faculty access required.', 'error')
            return redirect(url_for('main.report_form'))
        return f(*args, **kwargs)
    return decorated_function

def professional_login_required(f):
    """Decorator to require professional login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'professional_id' not in session:
            # Handle AJAX requests by returning 401 JSON instead of redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': ['Session expired. Please log in again.']}), 401
            return redirect(url_for('auth.login', pro=1))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require super admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_super_admin'):
            # Handle AJAX requests by returning 401 JSON instead of redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': ['SuperAdmin access required.']}), 401
            return redirect(url_for('superadmin.login'))
        return f(*args, **kwargs)
    return decorated_function
