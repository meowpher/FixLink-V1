"""
MIT-WPU Vyas Smart-Room Maintenance Tracker
Flask Application Factory
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

db = SQLAlchemy()


def create_app(config_name=None):
    """Application factory pattern for creating Flask app."""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Configuration — all secrets come from .env
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
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
    
    # Register blueprints
    from .routes import main_bp
    from .admin_routes import admin_bp
    from .auth_routes import auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp)
    
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
            
        # Create default admin user
        from .models import User
        if not User.query.filter_by(email='taha.piplodwala@mitwpu.edu.in').first():
            admin_user = User(
                name='Admin',
                email='taha.piplodwala@mitwpu.edu.in',
                is_admin=True,
                is_verified=True
            )
            admin_user.set_password('Taha10vesgono!')
            db.session.add(admin_user)
            db.session.commit()
    
    return app
