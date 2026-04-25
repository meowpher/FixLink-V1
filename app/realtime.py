"""
Pusher Real-time Utilities - Stateless replacement for SocketIO
"""
import os
import pusher
from flask import current_app, session

# Initialize Pusher client lazily
_pusher_client = None

def get_pusher():
    global _pusher_client
    if _pusher_client is None:
        app_id = os.environ.get('PUSHER_APP_ID')
        key = os.environ.get('PUSHER_KEY')
        secret = os.environ.get('PUSHER_SECRET')
        cluster = os.environ.get('PUSHER_CLUSTER')
        
        if all([app_id, key, secret, cluster]):
            _pusher_client = pusher.Pusher(
                app_id=app_id,
                key=key,
                secret=secret,
                cluster=cluster,
                ssl=True
            )
        else:
            # Fallback for development if keys are missing
            print("WARNING: Pusher credentials missing. Real-time features will be disabled.")
            return None
    return _pusher_client

def trigger_event(channel, event, data):
    """Trigger a Pusher event."""
    p = get_pusher()
    if p:
        try:
            p.trigger(channel, event, data)
        except Exception as e:
            print(f"Pusher trigger error: {str(e)}")

# ==================== NOTIFICATION FUNCTIONS ====================

def notify_professional_assigned(ticket, professional):
    """Notify professional that a ticket has been assigned to them."""
    channel = f'private-professional-{professional.id}'
    data = {
        'ticket_id': ticket.id,
        'ticket_number': ticket.room.number if ticket.room else None,
        'issue_type': ticket.issue_type,
        'description': ticket.description[:100] + '...' if len(ticket.description) > 100 else ticket.description,
        'time_limit_hours': ticket.time_limit_hours,
        'deadline': ticket.deadline_datetime.isoformat() + 'Z' if ticket.deadline_datetime else None
    }
    trigger_event(channel, 'new_assignment', data)
    
    # Trigger Web Push Notification
    try:
        from .utils import send_web_push
        send_web_push(
            professional_id=professional.id,
            title="New Job Assignment",
            body=f"You've been assigned to Room {ticket.room.number if ticket.room else 'Unknown'} for {ticket.issue_type}.",
            url="/professional"
        )
    except:
        pass

def notify_admin_job_started(ticket, professional):
    """Notify all admins that a professional has started a job."""
    from .models import User, Notification
    from . import db
    
    admins = User.query.filter_by(is_admin=True).all()
    data = {
        'ticket_id': ticket.id,
        'ticket_number': ticket.room.number if ticket.room else None,
        'professional_id': professional.id,
        'professional_name': professional.name,
        'started_at': ticket.job_started_at.isoformat() + 'Z' if ticket.job_started_at else None
    }
    
    # Broadcast to all admins
    trigger_event('private-admins', 'job_started', data)
    
    for admin in admins:
        # Persistent notification
        notif = Notification(
            user_id=admin.id,
            title="Job Started",
            message=f"Technician {professional.name} started job for room {ticket.room.number if ticket.room else 'Unknown'}.",
            type=Notification.TYPE_SYSTEM,
            link=f"/admin/?ticket_id={ticket.id}"
        )
        db.session.add(notif)
    db.session.commit()

def notify_admin_job_completed(ticket, professional):
    """Notify all admins that a professional has completed a job."""
    from .models import User, Notification
    from . import db
    
    admins = User.query.filter_by(is_admin=True).all()
    data = {
        'ticket_id': ticket.id,
        'ticket_number': ticket.room.number if ticket.room else None,
        'professional_id': professional.id,
        'professional_name': professional.name,
        'completed_at': ticket.job_completed_at.isoformat() + 'Z' if ticket.job_completed_at else None,
        'has_photo': ticket.completion_photo_filename is not None
    }
    
    trigger_event('private-admins', 'job_completed', data)
    
    for admin in admins:
        notif = Notification(
            user_id=admin.id,
            title="Job Completed",
            message=f"Technician {professional.name} completed job for room {ticket.room.number if ticket.room else 'Unknown'}.",
            type=Notification.TYPE_SYSTEM,
            link=f"/admin/?ticket_id={ticket.id}"
        )
        db.session.add(notif)
    db.session.commit()

def notify_admin_job_cancelled(ticket, professional, reason):
    """Notify all admins that a professional has cancelled a job."""
    from .models import User, Notification
    from . import db
    
    admins = User.query.filter_by(is_admin=True).all()
    data = {
        'ticket_id': ticket.id,
        'ticket_number': ticket.room.number if ticket.room else None,
        'professional_id': professional.id,
        'professional_name': professional.name,
        'reason': reason,
        'cancelled_at': ticket.cancelled_at.isoformat() + 'Z' if ticket.cancelled_at else None
    }
    
    trigger_event('private-admins', 'job_cancelled', data)
    
    for admin in admins:
        notif = Notification(
            user_id=admin.id,
            title="Job Cancelled",
            message=f"Technician {professional.name} cancelled job for room {ticket.room.number if ticket.room else 'Unknown'}. Reason: {reason}",
            type=Notification.TYPE_SYSTEM,
            link=f"/admin/?ticket_id={ticket.id}"
        )
        db.session.add(notif)
    db.session.commit()

def notify_admin_help_requested(help_request, requester, ticket):
    """Notify all admins that a professional is requesting help."""
    from .models import User, Notification
    from . import db
    
    admins = User.query.filter_by(is_admin=True).all()
    data = {
        'help_request_id': help_request.id,
        'ticket_id': ticket.id,
        'ticket_number': ticket.room.number if ticket.room else None,
        'requester_id': requester.id,
        'requester_name': requester.name,
        'requester_category': requester.category,
        'message': help_request.message,
        'requested_at': help_request.requested_at.isoformat() + 'Z' if help_request.requested_at else None
    }
    
    trigger_event('private-admins', 'help_requested', data)
    
    for admin in admins:
        notif = Notification(
            user_id=admin.id,
            title="Help Requested",
            message=f"Technician {requester.name} requested help for job {ticket.room.number if ticket.room else 'Unknown'}.",
            type=Notification.TYPE_HELP,
            link="/admin/help-requests"
        )
        db.session.add(notif)
    db.session.commit()

def notify_help_request_approved(help_request):
    """Notify professionals that help request was approved."""
    # Notify requester
    trigger_event(f'private-professional-{help_request.requester_professional_id}', 'help_approved', {
        'help_request_id': help_request.id,
        'helper_id': help_request.helper_professional_id,
        'helper_name': help_request.helper.name if help_request.helper else None,
        'ticket_id': help_request.ticket_id
    })
    
    # Notify helper
    if help_request.helper_professional_id:
        trigger_event(f'private-professional-{help_request.helper_professional_id}', 'assigned_as_helper', {
            'help_request_id': help_request.id,
            'ticket_id': help_request.ticket_id,
            'ticket_number': help_request.ticket.room.number if help_request.ticket and help_request.ticket.room else None,
            'requester_name': help_request.requester.name if help_request.requester else None
        })

def emit_chat_message(chat_message):
    """Emit a chat message to the involved parties."""
    from .models import ChatMessage, Notification, User, Professional
    from . import db
    
    data = {
        'id': chat_message.id,
        'sender_type': chat_message.sender_type,
        'sender_id': chat_message.sender_id,
        'receiver_type': chat_message.receiver_type,
        'receiver_id': chat_message.receiver_id,
        'message': chat_message.message,
        'timestamp': chat_message.timestamp.isoformat() + 'Z',
        'is_read': chat_message.is_read
    }
    
    # 1. Always notify admins
    trigger_event('private-admins', 'new_chat_message', data)
    
    # 2. Notify the involved professional
    prof_id = chat_message.sender_id if chat_message.sender_type == ChatMessage.SENDER_TYPE_PROFESSIONAL else chat_message.receiver_id
    trigger_event(f'private-professional-{prof_id}', 'new_chat_message', data)
    
            # 3. Create persistent notification if admin is receiver
    if chat_message.receiver_type == ChatMessage.SENDER_TYPE_ADMIN:
        sender = Professional.query.get(chat_message.sender_id)
        sender_name = sender.name if sender else "Technician"
        
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            notif = Notification(
                user_id=admin.id,
                title="New Message",
                message=f"New message from {sender_name}: {chat_message.message[:50]}...",
                type=Notification.TYPE_CHAT,
                link=f"/admin/chat?professional_id={chat_message.sender_id}"
            )
            db.session.add(notif)
        db.session.commit()

def emit_room_status_change(room, status_data):
    """Emit a room occupancy status change to all clients."""
    data = {
        'room_id': room.id,
        'room_number': room.number,
        'status': status_data['status'],
        'type': status_data.get('type'),
        'subject': status_data.get('subject'),
        'faculty': status_data.get('faculty'),
        'end_time': status_data.get('end_time')
    }
    trigger_event('public-room-updates', 'room_occupancy_changed', data)
