import pytest
from unittest.mock import patch
from app import create_app, db
from app.models import User, Professional

@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock external network calls like EmailJS, WebPush, and SocketIO for all tests."""
    with patch('app.utils.send_ticket_email') as mock_email, \
         patch('app.utils.send_web_push') as mock_push, \
         patch('flask_socketio.SocketIO.emit') as mock_emit:
        mock_email.return_value = True
        mock_push.return_value = True
        mock_emit.return_value = None
        yield

@pytest.fixture
def app():
    """Create and configure a new app instance for each test using in-memory SQLite."""
    # Override config for testing
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test_secret_key"
    })

    # Create the database and the database table
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def run_app_context(app):
    """Allows running db operations easily in testing context."""
    with app.app_context():
        yield

@pytest.fixture
def admin_user(app, run_app_context):
    """Fixture to create and return an admin user."""
    admin = User(name="Test Admin", email="admin@mitwpu.edu.in", is_admin=True)
    admin.set_password("password")
    db.session.add(admin)
    db.session.commit()
    return admin

@pytest.fixture
def student_user(app, run_app_context):
    """Fixture to create and return a regular student user."""
    student = User(name="Test Student", email="student@mitwpu.edu.in", prn="1234567890", is_admin=False)
    student.set_password("password")
    db.session.add(student)
    db.session.commit()
    return student

@pytest.fixture
def professional_user(app, run_app_context):
    """Fixture to create and return a professional."""
    prof = Professional(name="Test Pro", email="pro@mitwpu.edu.in", phone="1234567890", category="Electrician")
    prof.set_password("password")
    db.session.add(prof)
    db.session.commit()
    return prof
