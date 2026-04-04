"""
Database initialization and migration logic for FixLink.
Provides a central location for custom table/column checks and initial data setup.
"""
import os
import logging
from . import db

logger = logging.getLogger(__name__)

def init_db(app):
    """
    Perform database initialization tasks:
    1. Create all tables.
    2. Handle custom "migrations" (column checks for existing DBs).
    3. Create default admin user if configured.
    """
    with app.app_context():
        # 0. Import models to ensure they are registered with SQLAlchemy
        from . import models
        
        # 1. Create all tables
        db.create_all()
        
        # 2. Default admin user from environment variables
        from .models import User
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if admin_email and admin_password:
            if not User.query.filter_by(email=admin_email).first():
                admin_user = User(
                    name='Admin',
                    email=admin_email,
                    role=User.ROLE_ADMIN,
                    is_admin=True,
                    is_verified=True
                )
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
                logger.info(f'Default admin user created: {admin_email}')
        elif not admin_email or not admin_password:
             logger.warning('ADMIN_EMAIL or ADMIN_PASSWORD not set. Skipping default admin creation.')
