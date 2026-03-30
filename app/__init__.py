"""
MIT-WPU Vyas Smart-Room Maintenance Tracker
Flask Application Factory
"""
import os
import secrets
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from .socket_events import init_socketio

# SocketIO instance (will be initialized in create_app)
socketio = None

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)
db = SQLAlchemy()


def create_app(config_name=None):
    """Application factory pattern for creating Flask app."""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Configuration — all secrets come from .env
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        secret_key = secrets.token_hex(32)
        logger.warning(
            'SECRET_KEY is not set in environment. A temporary random key has been generated. '
            'Sessions will not persist across server restarts. Set SECRET_KEY in your .env file.'
        )
    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///vyas_tracker.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize SocketIO
    global socketio
    socketio = init_socketio(app)
    
    # Register blueprints
    from .routes import main_bp
    from .admin_routes import admin_bp
    from .auth_routes import auth_bp
    from .professional_routes import professional_bp
    from .superadmin_routes import superadmin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(superadmin_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Ensure reporter_id column exists (safe migration for existing DBs)
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(db.engine)
        ticket_columns = [col['name'] for col in inspector.get_columns('tickets')]
        if 'reporter_id' not in ticket_columns:
            db.session.execute(db.text(
                'ALTER TABLE tickets ADD COLUMN reporter_id INTEGER REFERENCES users(id)'
            ))
            db.session.commit()

        # Ensure profile_photo column exists on users table
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        if 'profile_photo' not in user_columns:
            db.session.execute(db.text(
                'ALTER TABLE users ADD COLUMN profile_photo VARCHAR(255)'
            ))
            db.session.commit()
        
        # Ensure new ticket columns exist for professional assignment
        ticket_columns = [col['name'] for col in inspector.get_columns('tickets')]
        new_ticket_columns = [
            ('assigned_professional_id', 'INTEGER REFERENCES professionals(id)'),
            ('complexity', 'VARCHAR(20)'),
            ('time_limit_hours', 'INTEGER'),
            ('deadline_datetime', 'DATETIME'),
            ('job_started_at', 'DATETIME'),
            ('job_completed_at', 'DATETIME'),
            ('completion_photo_filename', 'VARCHAR(255)'),
            ('cancellation_reason', 'TEXT'),
            ('cancelled_at', 'DATETIME'),
            ('cancelled_by_professional_id', 'INTEGER REFERENCES professionals(id)')
        ]
        for col_name, col_type in new_ticket_columns:
            if col_name not in ticket_columns:
                db.session.execute(db.text(
                    f'ALTER TABLE tickets ADD COLUMN {col_name} {col_type}'
                ))
                db.session.commit()
        
        # Ensure professional columns exist
        prof_columns = [col['name'] for col in inspector.get_columns('professionals')]
        new_prof_columns = [
            ('username', 'VARCHAR(50)'),
        ]
        for col_name, col_type in new_prof_columns:
            if col_name not in prof_columns:
                db.session.execute(db.text(
                    f'ALTER TABLE professionals ADD COLUMN {col_name} {col_type}'
                ))
                db.session.commit()
            
        # Create default admin user from environment variables
        from .models import User
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if admin_email and admin_password:
            if not User.query.filter_by(email=admin_email).first():
                admin_user = User(
                    name='Admin',
                    email=admin_email,
                    is_admin=True,
                    is_verified=True
                )
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
                logger.info(f'Default admin user created: {admin_email}')
        else:
            logger.warning(
                'ADMIN_EMAIL and ADMIN_PASSWORD are not set. '
                'No default admin user will be created. Set these in your .env file.'
            )
    
    # Register Jinja filters
    @app.template_filter('ist')
    def format_ist(value, format='%b %d, %H:%M'):
        if value is None:
            return ""
        from datetime import timedelta
        # UTC to IST is +5:30
        ist_time = value + timedelta(hours=5, minutes=30)
        return ist_time.strftime(format)
    
    return app
