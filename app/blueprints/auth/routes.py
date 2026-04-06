"""
Authentication Routes Blueprint
Handles unified login, signup, email verification, and password setup.
"""
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from ... import db, csrf
from ...models import User, Professional
from ...utils import send_verification_email, send_password_reset_email, ALLOWED_EXTENSIONS, allowed_file
from ...decorators import user_login_required
from ...api_utils import handle_api_errors, api_response
from ...realtime import get_pusher

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/pusher/auth', methods=['POST'])
@csrf.exempt
def pusher_authentication():
    """Authenticate private Pusher channels based on user session."""
    # Exempt from CSRF manually if we can't import csrf easily, 
    # but the standard way is using the @csrf.exempt decorator.
    # Since 'csrf' is initialized in app factory, we use the decorator if available.
    p = get_pusher()
    if not p:
        return jsonify({"error": "Pusher not configured"}), 500

    channel_name = request.form.get('channel_name')
    socket_id = request.form.get('socket_id')
    
    # Logic for Admin Private Channels
    if channel_name == 'private-admins':
        if 'user_id' in session and session.get('is_admin'):
            auth = p.authenticate(
                channel=channel_name,
                socket_id=socket_id
            )
            return jsonify(auth)
            
    # Logic for Professional Private Channels
    if channel_name.startswith('private-professional-'):
        prof_id_str = channel_name.replace('private-professional-', '')
        if 'professional_id' in session and str(session.get('professional_id')) == prof_id_str:
            auth = p.authenticate(
                channel=channel_name,
                socket_id=socket_id
            )
            return jsonify(auth)

    return jsonify({"error": "Forbidden"}), 403

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


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login for students, admins, and Job Certified Professionals."""
    # Redirect if already logged in
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('admin.dashboard')) if user.is_admin else redirect(url_for('main.report_form'))
    if 'professional_id' in session:
        return redirect(url_for('professional.dashboard'))
    
    # Check for special query parameter to show phone login (for professionals only)
    show_phone_hint = request.args.get('pro') == '1'
            
    if request.method == 'POST':
        login_input = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # Check if input is a phone number (Indian phone: 10 digits, possibly with +91)
        cleaned_input = login_input.replace('+91', '').replace('-', '').replace(' ', '')
        is_phone = cleaned_input.isdigit() and len(cleaned_input) == 10
        
        # Check if input looks like a username (no @ symbol, not all digits)
        is_username = '@' not in login_input and not cleaned_input.isdigit()
        
        professional = None
        user = None
        
        # Try to find professional first (by phone, username, or email)
        if is_phone:
            professional = Professional.query.filter_by(phone=cleaned_input, is_active=True).first()
        elif is_username:
            professional = Professional.query.filter_by(username=login_input, is_active=True).first()
        else:
            # Try email for both user and professional
            user = User.query.filter_by(email=login_input).first()
            if not user:
                professional = Professional.query.filter_by(email=login_input, is_active=True).first()
        
        # Check professional credentials
        if professional and professional.check_password(password):
            session['professional_id'] = professional.id
            session['professional_name'] = professional.name
            session['professional_category'] = professional.category
            flash(f'Welcome, {professional.name}!', 'success')
            return redirect(url_for('professional.dashboard'))
        
        # Check user credentials
        if user and user.check_password(password):
            if not user.is_verified:
                flash('Please verify your email address before logging in.', 'warning')
                return render_template('login.html', show_phone_hint=show_phone_hint)
                
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_email'] = user.email
            session['is_admin'] = user.is_admin
            
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('main.report_form'))
        
        # Invalid credentials
        if is_phone:
            flash('Invalid phone number or password. Note: Phone login is only for Job Certified Professionals.', 'error')
        elif is_username:
            flash('Invalid username or password. Note: Username login is only for Job Certified Professionals.', 'error')
        else:
            flash('Invalid email or password.', 'error')
            
    return render_template('login.html', show_phone_hint=show_phone_hint)


@auth_bp.route('/logout')
def logout():
    """Logout the current user or professional."""
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
@handle_api_errors
def upload_profile_photo():
    """Upload or update user profile photo."""
    if 'photo' not in request.files:
        return api_response(success=False, error="No file provided", status=400)

    file = request.files['photo']
    if not file or not file.filename:
        return api_response(success=False, error="No file selected", status=400)

    if not allowed_file(file.filename):
        return api_response(success=False, error="Invalid file type. Use PNG, JPG, GIF or WebP.", status=400)

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

    return api_response(data={'photo_url': f"/static/uploads/{filename}"}, message="Profile photo updated")


@auth_bp.route('/profile/remove-photo', methods=['POST'])
@user_login_required
@handle_api_errors
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
    return api_response(message="Profile photo removed")


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
