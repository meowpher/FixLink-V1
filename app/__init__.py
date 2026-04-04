"""
MIT-WPU Vyas Smart-Room Maintenance Tracker
Flask Application Factory
"""
import os
import secrets
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from .socket_events import init_socketio

# Core instances
db = SQLAlchemy()
migrate = Migrate()

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)


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
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.warning(
            'DATABASE_URL is not set. Falling back to local SQLite. '
            'Set DATABASE_URL in your .env file for production.'
        )
        database_url = 'sqlite:///vyas_tracker.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # PostgreSQL connection pool settings (ignored by SQLite)
    if database_url.startswith('postgresql'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 5,
            'pool_recycle': 300,
            'pool_pre_ping': True,
        }
    
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Cache
    from .cache import init_cache
    init_cache(app)
    
    # Security: CSRF Protection
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Security: Rate Limiting
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["1000 per day", "100 per hour"],
        storage_uri="memory://",
    )
    
    # Initialize SocketIO
    global socketio
    socketio = init_socketio(app)
    
    # Register blueprints
    from .blueprints.main import main_bp
    from .blueprints.admin import admin_bp
    from .blueprints.auth import auth_bp
    from .blueprints.professional import professional_bp
    from .blueprints.superadmin import superadmin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(superadmin_bp)
    
    # Initialize database and run migrations
    from .database import init_db
    init_db(app)
    
    # Start background scheduler for automated alerts
    from .scheduler import start_scheduler
    start_scheduler(app)
    
    # Global Session Refresh Hook
    @app.before_request
    def refresh_user_session():
        from flask import session
        from .models import User
        if 'user_id' in session and not session.get('is_super_admin'):
            user = User.query.get(session['user_id'])
            if user:
                # Sync critical flags
                session['is_admin'] = user.is_admin
                session['user_role'] = user.role
    
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
