"""
SocketIO Events - WebSocket handling for real-time chat and notifications
"""
from flask import session
from flask_socketio import emit, join_room, leave_room

# Store socketio instance for later use
socketio = None


def init_socketio(app):
    """Initialize SocketIO with the Flask app."""
    global socketio
    from flask_socketio import SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    register_events(socketio)
    return socketio


def register_events(sio):
    """Register SocketIO event handlers."""
    from .models import ChatMessage, Professional, User, Notification
    from . import db
    
    @sio.on('connect')
    def handle_connect():
        """Handle client connection."""
        if 'user_id' in session:
            # Admin connected
            join_room(f'admin_{session["user_id"]}')
            join_room('admins') # All admins join a common room
            emit('connected', {'role': 'admin', 'id': session['user_id']})
        elif 'professional_id' in session:
            # Professional connected
            join_room(f'professional_{session["professional_id"]}')
            emit('connected', {'role': 'professional', 'id': session['professional_id']})
    
    @sio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        if 'user_id' in session:
            leave_room(f'admin_{session["user_id"]}')
        elif 'professional_id' in session:
            leave_room(f'professional_{session["professional_id"]}')
    
    @sio.on('join_chat')
    def handle_join_chat(data):
        """Join a chat room with a specific user."""
        room = data.get('room')
        if room:
            join_room(room)
            emit('joined_chat', {'room': room})
    
    @sio.on('send_message')
    def handle_send_message(data):
        """Handle incoming chat message."""
        message = data.get('message')
        receiver_type = data.get('receiver_type')
        receiver_id = data.get('receiver_id')
        
        if 'user_id' in session:
            # Admin sending message
            sender_type = ChatMessage.SENDER_TYPE_ADMIN
            sender_id = session['user_id']
            room = f'professional_{receiver_id}'
        elif 'professional_id' in session:
            # Professional sending message
            sender_type = ChatMessage.SENDER_TYPE_PROFESSIONAL
            sender_id = session['professional_id']
            room = f'admin_{receiver_id}'
        else:
            return
        
        # Save message to database
        chat_message = ChatMessage(
            sender_type=sender_type,
            sender_id=sender_id,
            receiver_type=receiver_type,
            receiver_id=receiver_id,
            message=message
        )
        db.session.add(chat_message)
        db.session.commit()
        
        # Emit to receiver
        emit('new_message', {
            'message': message,
            'sender_type': sender_type,
            'sender_id': sender_id,
            'timestamp': chat_message.timestamp.isoformat() + 'Z'
        }, room=room)
        
        # Confirm to sender
        emit('message_sent', {'message_id': chat_message.id})


# ==================== NOTIFICATION FUNCTIONS ====================

def notify_professional_assigned(ticket, professional):
    """Notify professional that a ticket has been assigned to them."""
    if socketio:
        room = f'professional_{professional.id}'
        socketio.emit('new_assignment', {
            'ticket_id': ticket.id,
            'ticket_number': ticket.room.number if ticket.room else None,
            'issue_type': ticket.issue_type,
            'description': ticket.description[:100] + '...' if len(ticket.description) > 100 else ticket.description,
            'time_limit_hours': ticket.time_limit_hours,
            'deadline': ticket.deadline_datetime.isoformat() + 'Z' if ticket.deadline_datetime else None
        }, room=room)
        
        # Trigger Web Push Notification
        try:
            from .utils import send_web_push
            send_web_push(
                professional_id=professional.id,
                title="New Job Assignment",
                body=f"You've been assigned to Room {ticket.room.number if ticket.room else 'Unknown'} for {ticket.issue_type}.",
                url="/professional"
            )
        except Exception as e:
            pass


def notify_admin_job_started(ticket, professional):
    """Notify admin that a professional has started a job."""
    from .models import User, Notification
    from . import db
    if socketio:
        # Notify all admins
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            # Create persistent notification
            notif = Notification(
                user_id=admin.id,
                title="Job Started",
                message=f"Technician {professional.name} started job for room {ticket.room.number if ticket.room else 'Unknown'}.",
                type=Notification.TYPE_SYSTEM,
                link=f"/admin/?ticket_id={ticket.id}"
            )
            db.session.add(notif)
            
            room = f'admin_{admin.id}'
            socketio.emit('job_started', {
                'ticket_id': ticket.id,
                'ticket_number': ticket.room.number if ticket.room else None,
                'professional_id': professional.id,
                'professional_name': professional.name,
                'started_at': ticket.job_started_at.isoformat() + 'Z' if ticket.job_started_at else None
            }, room=room)
            
            # Trigger Web Push for Admin
            try:
                from .utils import send_web_push
                send_web_push(
                    user_id=admin.id,
                    title="Job Started",
                    body=f"Technician {professional.name} started job for room {ticket.room.number if ticket.room else 'Unknown'}.",
                    url=f"/admin/?ticket_id={ticket.id}"
                )
            except Exception as e:
                pass
        db.session.commit()


def notify_admin_job_completed(ticket, professional):
    """Notify admin that a professional has completed a job."""
    from .models import User, Notification
    from . import db
    if socketio:
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            # Create persistent notification
            notif = Notification(
                user_id=admin.id,
                title="Job Completed",
                message=f"Technician {professional.name} completed job for room {ticket.room.number if ticket.room else 'Unknown'}.",
                type=Notification.TYPE_SYSTEM,
                link=f"/admin/?ticket_id={ticket.id}"
            )
            db.session.add(notif)
            
            room = f'admin_{admin.id}'
            socketio.emit('job_completed', {
                'ticket_id': ticket.id,
                'ticket_number': ticket.room.number if ticket.room else None,
                'professional_id': professional.id,
                'professional_name': professional.name,
                'completed_at': ticket.job_completed_at.isoformat() + 'Z' if ticket.job_completed_at else None,
                'has_photo': ticket.completion_photo_filename is not None
            }, room=room)
            
            # Trigger Web Push for Admin
            try:
                from .utils import send_web_push
                send_web_push(
                    user_id=admin.id,
                    title="Job Completed",
                    body=f"Technician {professional.name} completed job for room {ticket.room.number if ticket.room else 'Unknown'}.",
                    url=f"/admin/?ticket_id={ticket.id}"
                )
            except Exception as e:
                pass

        db.session.commit()

def notify_admin_job_cancelled(ticket, professional, reason):
    """Notify admin that a professional has cancelled a job."""
    from .models import User, Notification
    from . import db
    if socketio:
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            # Create persistent notification
            notif = Notification(
                user_id=admin.id,
                title="Job Cancelled",
                message=f"Technician {professional.name} cancelled job for room {ticket.room.number if ticket.room else 'Unknown'}. Reason: {reason}",
                type=Notification.TYPE_SYSTEM,
                link=f"/admin/?ticket_id={ticket.id}"
            )
            db.session.add(notif)
            
            room = f'admin_{admin.id}'
            socketio.emit('job_cancelled', {
                'ticket_id': ticket.id,
                'ticket_number': ticket.room.number if ticket.room else None,
                'professional_id': professional.id,
                'professional_name': professional.name,
                'reason': reason,
                'cancelled_at': ticket.cancelled_at.isoformat() + 'Z' if ticket.cancelled_at else None
            }, room=room)
            
            # Trigger Web Push for Admin
            try:
                from .utils import send_web_push
                send_web_push(
                    user_id=admin.id,
                    title="Job Cancelled",
                    body=f"Technician {professional.name} cancelled job for room {ticket.room.number if ticket.room else 'Unknown'}.",
                    url=f"/admin/?ticket_id={ticket.id}"
                )
            except Exception as e:
                pass
        db.session.commit()


def notify_admin_help_requested(help_request, requester, ticket):
    """Notify admin that a professional is requesting help."""
    from .models import User, Notification
    from . import db
    if socketio:
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            # Create persistent notification
            notif = Notification(
                user_id=admin.id,
                title="Help Requested",
                message=f"Technician {requester.name} requested help for job {ticket.room.number if ticket.room else 'Unknown'}.",
                type=Notification.TYPE_HELP,
                link=f"/admin/help-requests" # Assuming this route exists
            )
            db.session.add(notif)
            
            # Emit to unified admins room for real-time dashboard updates
            socketio.emit('help_requested', {
                'help_request_id': help_request.id,
                'ticket_id': ticket.id,
                'ticket_number': ticket.room.number if ticket.room else None,
                'requester_id': requester.id,
                'requester_name': requester.name,
                'requester_category': requester.category,
                'message': help_request.message,
                'requested_at': help_request.requested_at.isoformat() + 'Z' if help_request.requested_at else None
            }, room='admins')
        db.session.commit()


def notify_help_request_approved(help_request):
    """Notify professionals that help request was approved."""
    if socketio:
        # Notify requester
        requester_room = f'professional_{help_request.requester_professional_id}'
        socketio.emit('help_approved', {
            'help_request_id': help_request.id,
            'helper_id': help_request.helper_professional_id,
            'helper_name': help_request.helper.name if help_request.helper else None,
            'ticket_id': help_request.ticket_id
        }, room=requester_room)
        
        # Notify helper
        if help_request.helper_professional_id:
            helper_room = f'professional_{help_request.helper_professional_id}'
            socketio.emit('assigned_as_helper', {
                'help_request_id': help_request.id,
                'ticket_id': help_request.ticket_id,
                'ticket_number': help_request.ticket.room.number if help_request.ticket and help_request.ticket.room else None,
                'requester_name': help_request.requester.name if help_request.requester else None
            }, room=helper_room)


def notify_help_request_rejected(help_request):
    """Notify professional that help request was rejected."""
    if socketio:
        room = f'professional_{help_request.requester_professional_id}'
        socketio.emit('help_rejected', {
            'help_request_id': help_request.id,
            'ticket_id': help_request.ticket_id
        }, room=room)


def emit_chat_message(chat_message):
    """Emit a chat message to the appropriate rooms."""
    from .models import ChatMessage
    if socketio:
        # Determine the professional involved (sender or receiver)
        prof_id = chat_message.sender_id if chat_message.sender_type == ChatMessage.SENDER_TYPE_PROFESSIONAL else chat_message.receiver_id
        prof_room = f'professional_{prof_id}'
        
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
        
        # Always emit to 'admins' so all admins are in sync
        socketio.emit('new_chat_message', data, room='admins')
        
        # Always emit to the involved professional's room
        socketio.emit('new_chat_message', data, room=prof_room)
        
        # Create persistent notification for admins when receiving chat
        if chat_message.receiver_type == ChatMessage.SENDER_TYPE_ADMIN:
            from .models import Notification, User
            from . import db
            # Find sender name
            from .models import Professional
            sender = Professional.query.get(chat_message.sender_id)
            sender_name = sender.name if sender else "Technician"
            
            # Notify ALL admins
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
