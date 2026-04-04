import time
import threading
import os
from datetime import datetime, timedelta
from . import db
from .models import Ticket, User, Professional
from .utils import send_web_push

def check_for_alerts(app):
    with app.app_context():
        now = datetime.utcnow()
        
        # 1. Unassigned Ticket Alerts (>24h)
        # Tickets in 'open' or 'cancelled' status for more than 24h
        unassigned_threshold = now - timedelta(hours=24)
        unassigned_tickets = Ticket.query.filter(
            Ticket.status.in_([Ticket.STATUS_OPEN, Ticket.STATUS_CANCELLED]),
            Ticket.created_at < unassigned_threshold,
            (Ticket.last_notification_sent_at == None) | (Ticket.last_notification_sent_at < now - timedelta(hours=24))
        ).all()
        
        if unassigned_tickets:
            admins = User.query.filter_by(is_admin=True).all()
            for ticket in unassigned_tickets:
                for admin in admins:
                    try:
                        send_web_push(
                            user_id=admin.id,
                            title="Unassigned Ticket Alert",
                            body=f"Ticket #{ticket.id} (Room {ticket.room.number if ticket.room else '?'}) has been unassigned for >24h.",
                            url=f"/admin/?ticket_id={ticket.id}"
                        )
                    except:
                        pass
                ticket.last_notification_sent_at = now
            db.session.commit()

        # 2. Overdue Ticket Alerts
        # Tickets with a deadline in the past and not fixed/cancelled
        overdue_tickets = Ticket.query.filter(
            Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS]),
            Ticket.deadline_datetime < now,
            (Ticket.last_notification_sent_at == None) | (Ticket.last_notification_sent_at < now - timedelta(hours=12))
        ).all()
        
        if overdue_tickets:
            admins = User.query.filter_by(is_admin=True).all()
            for ticket in overdue_tickets:
                for admin in admins:
                    try:
                        send_web_push(
                            user_id=admin.id,
                            title="Overdue Ticket Alert",
                            body=f"Ticket #{ticket.id} (Room {ticket.room.number if ticket.room else '?'}) is past its deadline!",
                            url=f"/admin/?ticket_id={ticket.id}"
                        )
                    except:
                        pass
                ticket.last_notification_sent_at = now
            db.session.commit()

        # 3. Professional Inactivity Alerts (>4h in-progress)
        inactivity_threshold = now - timedelta(hours=4)
        inactive_tickets = Ticket.query.filter(
            Ticket.status == Ticket.STATUS_IN_PROGRESS,
            Ticket.job_started_at < inactivity_threshold,
            (Ticket.last_notification_sent_at == None) | (Ticket.last_notification_sent_at < now - timedelta(hours=4))
        ).all()
        
        if inactive_tickets:
            for ticket in inactive_tickets:
                if ticket.assigned_professional_id:
                    try:
                        send_web_push(
                            professional_id=ticket.assigned_professional_id,
                            title="Inactivity Alert",
                            body=f"Job for Room {ticket.room.number if ticket.room else '?'} has been in-progress for >4h. Please update the status.",
                            url="/professional"
                        )
                    except:
                        pass
                ticket.last_notification_sent_at = now
            db.session.commit()

        # 4. Critical Asset Health Alerts (<30% score)
        try:
            from .analytics import get_critical_assets
            critical_assets = get_critical_assets(limit=10)
            for asset_data in critical_assets:
                if asset_data['score'] < 30:
                    admins = User.query.filter_by(is_admin=True).all()
                    for admin in admins:
                        send_web_push(
                            user_id=admin.id,
                            title="Critical Asset Health Alert",
                            body=f"Asset '{asset_data['name']}' in Room {asset_data['room']} has a critical health score of {asset_data['score']}%!",
                            url="/admin/analytics"
                        )
        except Exception as e:
            print(f"Critical Asset Alert Error: {str(e)}")

def scheduler_loop(app):
    # Minimal wait to let the app start fully
    time.sleep(10)
    print("Background scheduler started.")
    while True:
        try:
            check_for_alerts(app)
        except Exception as e:
            # We use print here because we are in a background thread without easy logger access
            print(f"Scheduler error: {str(e)}")
        
        # Check every 30 minutes (1800 seconds)
        time.sleep(1800)

def start_scheduler(app):
    """Start the background scheduler thread."""
    # Ensure we only start one thread even with Flask reloader
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        thread = threading.Thread(target=scheduler_loop, args=(app,), daemon=True)
        thread.start()
