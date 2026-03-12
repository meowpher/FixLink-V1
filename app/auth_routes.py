"""
Authentication Routes Blueprint
Handles unified login, signup, email verification, and password setup.
"""
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from . import db
from .models import User
from .email_utils import send_verification_email, send_password_reset_email

auth_bp = Blueprint('auth', __name__)

def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-verification-salt')

def confirm_verification_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt='email-verification-salt',
            max_age=expiration
        )
    except:
        return False
    return email


def user_login_required(f):
    """Decorator to require user login (reporter or admin)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login for students and admins."""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('admin.dashboard')) if user.is_admin else redirect(url_for('main.report_form'))
            
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_verified:
                flash('Please verify your email address before logging in.', 'warning')
                return render_template('login.html')
                
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['is_admin'] = user.is_admin
            
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('main.report_form'))
        else:
            flash('Invalid email or password.', 'error')
            
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Logout the current user."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Student signup form demanding @mitwpu.edu.in email."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        prn = request.form.get('prn', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        if not email.endswith('@mitwpu.edu.in'):
            flash('You must use a valid @mitwpu.edu.in email address.', 'error')
            return render_template('signup.html', name=name, prn=prn, email=email)
            
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.is_verified:
                flash('This email is already registered and verified. Please log in.', 'warning')
                return render_template('signup.html', name=name, prn=prn, email=email)
            else:
                # Account exists but not verified — refresh token and resend
                token = generate_verification_token(email)
                existing_user.verification_token = token
                db.session.commit()
                verification_link = url_for('auth.verify_email', token=token, _external=True)
                email_sent = False
                try:
                    email_sent = send_verification_email(email, existing_user.name, verification_link)
                except Exception as e:
                    print(f"ERROR: Failed to send verification email: {e}")
                return render_template(
                    'signup_success.html',
                    email=email,
                    email_sent=email_sent,
                    verification_link=verification_link
                )

        # Create new unverified user
        token = generate_verification_token(email)
        user = User(
            name=name,
            prn=prn,
            email=email,
            is_verified=False,
            verification_token=token
        )
        db.session.add(user)
        db.session.commit()

        # Send verification email — proceed to success page regardless of email outcome
        verification_link = url_for('auth.verify_email', token=token, _external=True)
        email_sent = False
        try:
            email_sent = send_verification_email(email, name, verification_link)
        except Exception as e:
            print(f"ERROR: Failed to send verification email: {e}")

        return render_template(
            'signup_success.html',
            email=email,
            email_sent=email_sent,
            verification_link=verification_link
        )
        
    return render_template('signup.html')


@auth_bp.route('/verify/<token>')
def verify_email(token):
    """Verify the email and direct user to setup their password."""
    email = confirm_verification_token(token)
    if not email:
        flash('The verification link is invalid or has expired.', 'error')
        return redirect(url_for('auth.signup'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.signup'))
        
    if user.is_verified:
        flash('Account already verified. Please login.', 'info')
        return redirect(url_for('auth.login'))
        
    # Valid token, let them set password
    session['setup_email'] = email
    return redirect(url_for('auth.setup_password'))


@auth_bp.route('/setup-password', methods=['GET', 'POST'])
def setup_password():
    """Form to establish a password after verification."""
    email = session.get('setup_email')
    if not email:
        flash('Session expired. Please use the verification link again.', 'error')
        return redirect(url_for('auth.signup'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('setup_password.html')
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('setup_password.html')
            
        user = User.query.filter_by(email=email).first()
        user.set_password(password)
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        
        # Clear setup session and redirect to login
        session.pop('setup_email', None)
        flash('Your password has been set! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('setup_password.html')


@auth_bp.route('/profile/upload-photo', methods=['POST'])
@user_login_required
def upload_profile_photo():
    """Upload or update user profile photo."""
    import os
    from werkzeug.utils import secure_filename
    from datetime import datetime

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['photo']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type. Use PNG, JPG, GIF or WebP.'}), 400

    user = User.query.get(session['user_id'])

    # Delete old photo if it exists
    if user.profile_photo:
        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.profile_photo)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new photo
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"profile_{user.id}_{timestamp}_{filename}"
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    user.profile_photo = filename
    db.session.commit()

    return jsonify({'success': True, 'photo_url': f"/static/uploads/{filename}"})


@auth_bp.route('/profile/remove-photo', methods=['POST'])
@user_login_required
def remove_profile_photo():
    """Remove user profile photo."""
    import os
    user = User.query.get(session['user_id'])
    if user.profile_photo:
        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.profile_photo)
        if os.path.exists(old_path):
            os.remove(old_path)
        user.profile_photo = None
        db.session.commit()
    return jsonify({'success': True})


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Send a password reset email."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        # Always show the same message to avoid user enumeration
        if user and user.is_verified:
            token = generate_verification_token(email)
            user.verification_token = token
            db.session.commit()
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            email_sent = False
            try:
                email_sent = send_password_reset_email(email, user.name, reset_link)
            except Exception as e:
                print(f'ERROR sending reset email: {e}')

            return render_template(
                'forgot_password_sent.html',
                email=email,
                email_sent=email_sent,
                reset_link=reset_link
            )
        else:
            # No account or unverified — show a generic sent page anyway
            return render_template(
                'forgot_password_sent.html',
                email=email,
                email_sent=False,
                reset_link=None
            )

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Verify token and allow the user to set a new password."""
    email = confirm_verification_token(token)
    if not email:
        flash('The reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Account not found.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('reset_password.html', token=token)

        user.set_password(password)
        user.verification_token = None
        user.is_verified = True
        db.session.commit()
        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)
