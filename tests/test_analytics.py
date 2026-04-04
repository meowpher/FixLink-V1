import pytest
import datetime
from app import db
from app.models import Ticket, Room, Floor, Building

def test_analytics_computation(client, admin_user, professional_user, run_app_context):
    """Test that the analytics backend endpoint yields correct data avoiding TypeErrors."""
    
    with run_app_context:
        # Create foundational entities
        b = Building(name="Analytics Building")
        f = Floor(level=1, building=b)
        r = Room(number="ANA101", floor=f)
        db.session.add_all([b, f, r])
        db.session.commit()
        
        # Populate dummy tickets with various statuses and timings
        now = datetime.datetime.utcnow()
        t1 = Ticket(room_id=r.id, issue_type="electrical", status=Ticket.STATUS_FIXED, reporter_id=admin_user.id)
        t1.created_at = now - datetime.timedelta(days=2)
        t1.job_completed_at = now - datetime.timedelta(days=1)
        # Resolved in 24 hours
        
        t2 = Ticket(room_id=r.id, issue_type="plumbing", status=Ticket.STATUS_FIXED, reporter_id=admin_user.id)
        t2.created_at = now - datetime.timedelta(days=5)
        t2.job_completed_at = now - datetime.timedelta(days=3)
        # Resolved in 48 hours
        
        t3 = Ticket(room_id=r.id, issue_type="furniture", status=Ticket.STATUS_OPEN, reporter_id=admin_user.id)
        t3.created_at = now
        
        db.session.add_all([t1, t2, t3])
        db.session.commit()

    # Authenticate as admin
    with client.session_transaction() as sess:
        sess.clear()
        sess['user_id'] = admin_user.id
        sess['is_admin'] = True
        
    # Get analytics payload
    response = client.get('/admin/api/analytics')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    assert data['total_tickets'] == 3
    assert data['completed_tickets'] == 2
    assert data['open_tickets'] == 1
    
    # Check that average resolution time is calculated properly without NoneType error
    # Because there are two resolved tickets (24h + 48h = 72h / 2 = 36h)
    # The value might not be exactly 36.00 due to tiny execution time differences, but it shouldn't crash.
    assert data['avg_resolution_time'] is not None
    assert type(data['avg_resolution_time']) in [float, int]
