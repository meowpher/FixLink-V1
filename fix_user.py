import sys
sys.path.insert(0, '/home/taha-mustafa/Desktop/FixLink-F')
from app import create_app, db
from app.models import User
app = create_app()
app.app_context().push()
try:
    u = User.query.filter_by(email='taha.piplodwala@mitwpu.edu.in').first()
    if not u:
        u = User(name='Admin', email='taha.piplodwala@mitwpu.edu.in', is_admin=True, is_verified=True)
        db.session.add(u)
    u.set_password('Taha10vesgono!')
    u.is_admin = True
    u.is_verified = True
    db.session.commit()
    print("USER UPDATED SUCCESSFULLY")
except Exception as e:
    print(f"ERROR: {e}")
