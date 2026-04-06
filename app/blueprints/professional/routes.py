"""
Professional Routes Blueprint - Worker Dashboard and Task Management
"""
import os
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from ... import db
from ...models import Professional, Ticket, HelpRequest, ChatMessage, Room, Asset, User, Notification
from ...utils import allowed_file
from ...decorators import professional_login_required
from ...api_utils import handle_api_errors, api_response

professional_bp = Blueprint('professional', __name__, url_prefix='/professional')


@professional_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Professional login page - now supports username, phone, or email."""
    # Check if already logged in as professional
    if 'professional_id' in session:
        return redirect(url_for('professional.dashboard'))
    
    # If logged in as user/admin, redirect to main login
    if 'user_id' in session:
        return redirect(url_for('auth.login'))
    
    # Redirect to unified login page (professionals can use ?pro=1 hint there)
    return redirect(url_for('auth.login', pro=1))


@professional_bp.route('/logout')
def logout():
    """Logout the current professional."""
    session.pop('professional_id', None)
    session.pop('professional_name', None)
    session.pop('professional_category', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('professional.login'))


@professional_bp.route('/dashboard')
@professional_login_required
def dashboard():
    """Professional dashboard - view assigned tasks."""
    professional = Professional.query.get(session['professional_id'])
    
    # Get all assigned tickets for this professional where they are the primary appointee
    primary_tickets = Ticket.query.filter_by(
        assigned_professional_id=professional.id
    ).filter(
        Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])
    ).all()
    
    for t in primary_tickets:
        t.role = 'Primary'

    # Get tickets where this professional is an approved helper
    helper_requests = HelpRequest.query.filter_by(
        helper_professional_id=professional.id,
        status=HelpRequest.STATUS_APPROVED
    ).all()
    
    helper_tickets = []
    for hr in helper_requests:
        if hr.ticket.status in [Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS]:
            hr.ticket.role = 'Helper'
            helper_tickets.append(hr.ticket)
            
    # Combine and sort by creation date
    assigned_tickets = sorted(primary_tickets + helper_tickets, key=lambda x: x.created_at, reverse=True)
    
    # Get completed tickets (for history)
    completed_tickets = Ticket.query.filter_by(
        assigned_professional_id=professional.id,
        status=Ticket.STATUS_FIXED
    ).order_by(Ticket.job_completed_at.desc()).limit(10).all()
    
    # Get pending help requests (sent by this professional)
    help_requests = HelpRequest.query.filter_by(
        requester_professional_id=professional.id
    ).filter(
        HelpRequest.status == HelpRequest.STATUS_PENDING
    ).all()
    
    # Category display names
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    return render_template('professional/dashboard.html',
                         professional=professional,
                         category_name=category_names.get(professional.category, professional.category),
                         assigned_tickets=assigned_tickets,
                         completed_tickets=completed_tickets,
                         help_requests=help_requests,
                         complexity_choices=Ticket.COMPLEXITY_CHOICES,
                         vapid_public_key=os.environ.get('VAPID_PUBLIC_KEY', ''))


@professional_bp.route('/chat')
@professional_login_required
def chat():
    """Professional chat page."""
    professional = Professional.query.get(session['professional_id'])
    
    # Category display names
    category_names = {
        Professional.CATEGORY_IT: 'IT Technician',
        Professional.CATEGORY_ELECTRICIAN: 'Electrician',
        Professional.CATEGORY_PLUMBER: 'Plumber',
        Professional.CATEGORY_CARPENTER: 'Carpenter'
    }
    
    return render_template('professional/chat.html',
                         professional=professional,
                         category_name=category_names.get(professional.category, professional.category))


@professional_bp.route('/history')
@professional_login_required
def history():
    """Professional task history."""
    professional = Professional.query.get(session['professional_id'])
    
    # Get all completed tickets for this professional
    completed_tickets = Ticket.query.filter_by(
        assigned_professional_id=professional.id,
        status=Ticket.STATUS_FIXED
    ).order_by(Ticket.job_completed_at.desc()).all()
    
    return render_template('professional/history.html',
                         professional=professional,
                         completed_tickets=completed_tickets)


@professional_bp.route('/task/<int:ticket_id>')
@professional_login_required
def task_detail(ticket_id):
    """View detailed task information."""
    professional = Professional.query.get(session['professional_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Ensure this ticket is assigned to this professional
    if ticket.assigned_professional_id != professional.id:
        flash('You do not have permission to view this task.', 'error')
        return redirect(url_for('professional.dashboard'))
    
    # Get chat history with admin
    chat_messages = ChatMessage.query.filter(
        ((ChatMessage.sender_type == 'professional') & (ChatMessage.sender_id == professional.id)) |
        ((ChatMessage.receiver_type == 'professional') & (ChatMessage.receiver_id == professional.id))
    ).order_by(ChatMessage.timestamp.asc()).limit(50).all()
    
    # Get help requests for this ticket
    help_requests = HelpRequest.query.filter_by(ticket_id=ticket_id).all()
    
    return render_template('professional/task_detail.html',
                         professional=professional,
                         ticket=ticket,
                         chat_messages=chat_messages,
                         help_requests=help_requests)


# API Endpoints for Task Actions

@professional_bp.route('/api/task/<int:ticket_id>/start', methods=['POST'])
@professional_login_required
@handle_api_errors
def start_task(ticket_id):
    """Start a task - update status and notify admin."""
    professional = Professional.query.get(session['professional_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if ticket.assigned_professional_id != professional.id:
        return api_response(success=False, error='Not authorized - ticket not assigned to you', status=403)
    
    current_status = ticket.status
    expected_status = Ticket.STATUS_ASSIGNED
    
    if current_status != expected_status:
        return api_response(success=False, error=f'Task is not in assigned state. Current status: {current_status}, Expected: {expected_status}', status=400)

    # Ensure professional doesn't have another job in progress
    active_task = Ticket.query.filter(
        Ticket.assigned_professional_id == professional.id,
        Ticket.status == Ticket.STATUS_IN_PROGRESS,
        Ticket.id != ticket_id
    ).first()
    
    if active_task:
        return api_response(success=False, error=f'You already have an active task in progress (# {active_task.id}). Please complete or cancel it first.', status=400)
    
    ticket.status = Ticket.STATUS_IN_PROGRESS
    ticket.job_started_at = datetime.utcnow()
    db.session.commit()
    
    # Notify admin via notification system
    from ...realtime import notify_admin_job_started
    notify_admin_job_started(ticket, professional)
    
    # Notify reporter via EmailJS (Best effort)
    from ...utils import send_ticket_email
    try:
        send_ticket_email(ticket, action='in-progress')
    except Exception as e:
        current_app.logger.error(f"Email failed: {str(e)}")
    
    return jsonify({
        'success': True,
        'message': 'Job started successfully',
        'job_started_at': ticket.job_started_at.isoformat()
    })


@professional_bp.route('/api/task/<int:ticket_id>/complete', methods=['POST'])
@professional_login_required
@handle_api_errors
def complete_task(ticket_id):
    """Complete a task - upload photo and notify admin."""
    professional = Professional.query.get(session['professional_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if ticket.assigned_professional_id != professional.id:
        return api_response(success=False, error="Not authorized", status=403)
    
    if ticket.status != Ticket.STATUS_IN_PROGRESS:
        return api_response(success=False, error="Task must be in progress to complete", status=400)
    
    # Handle photo upload
    completion_photo = None
    if 'completion_photo' in request.files:
        file = request.files['completion_photo']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"completion_{ticket_id}_{timestamp}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            completion_photo = filename
    
    ticket.status = Ticket.STATUS_FIXED
    ticket.job_completed_at = datetime.utcnow()
    ticket.completion_photo_filename = completion_photo
    ticket.fixed_at = datetime.utcnow()
    
    # Mark asset as working if applicable
    if ticket.asset_id:
        asset = Asset.query.get(ticket.asset_id)
        if asset:
            asset.status = Asset.STATUS_WORKING
    
    db.session.commit()
    
    # Notify admin
    from ...realtime import notify_admin_job_completed
    notify_admin_job_completed(ticket, professional)
    
    # Notify reporter via EmailJS
    from ...utils import send_ticket_email
    send_ticket_email(ticket, action='fixed')
    
    return jsonify({
        'success': True,
        'message': 'Job completed successfully',
        'job_completed_at': ticket.job_completed_at.isoformat()
    })


@professional_bp.route('/api/task/<int:ticket_id>/cancel', methods=['POST'])
@professional_login_required
@handle_api_errors
def cancel_task(ticket_id):
    """Cancel a task with reason - limited tracking per day."""
    professional = Professional.query.get(session['professional_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if ticket.assigned_professional_id != professional.id:
        return api_response(success=False, error="Not authorized", status=403)
    
    if ticket.status not in [Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS]:
        return api_response(success=False, error="Cannot cancel this task", status=400)
    
    from ...api_utils import validate_json
    data, error = validate_json(['reason'])
    if error: return error
    reason = data.get('reason', '').strip()
    
    ticket.status = Ticket.STATUS_CANCELLED
    ticket.cancellation_reason = reason
    ticket.cancelled_at = datetime.utcnow()
    ticket.cancelled_by_professional_id = professional.id
    
    # Unassign the professional
    ticket.assigned_professional_id = None
    db.session.commit()
    
    # Notify admin via Socket.IO, WebPush and Persistent Notification
    from ...realtime import notify_admin_job_cancelled
    notify_admin_job_cancelled(ticket, professional, reason)
    
    return jsonify({
        'success': True,
        'message': "Job cancelled successfully. Admin will reassign.",
        'cancelled_at': ticket.cancelled_at.isoformat()
    })


@professional_bp.route('/api/task/<int:ticket_id>/complexity', methods=['POST'])
@professional_login_required
@handle_api_errors
def set_complexity(ticket_id):
    """Set task complexity (Low/Medium/High)."""
    professional = Professional.query.get(session['professional_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if ticket.assigned_professional_id != professional.id:
        return api_response(success=False, error="Not authorized", status=403)
    
    data = request.get_json()
    complexity = data.get('complexity')
    
    if complexity not in Ticket.COMPLEXITY_CHOICES:
        return api_response(success=False, error="Invalid complexity level", status=400)
    
    ticket.complexity = complexity
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f"Complexity set to {complexity}"
    })


# Help Request Endpoints

@professional_bp.route('/api/task/<int:ticket_id>/request-help', methods=['POST'])
@professional_login_required
@handle_api_errors
def request_help(ticket_id):
    """Request help from another professional - goes to admin for approval."""
    professional = Professional.query.get(session['professional_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if ticket.assigned_professional_id != professional.id:
        return api_response(success=False, error="Not authorized", status=403)
    
    from ...api_utils import validate_json
    data, error = validate_json(['message'])
    if error: return error
    message = data.get('message', '').strip()
    
    help_request = HelpRequest(
        ticket_id=ticket_id,
        requester_professional_id=professional.id,
        message=message,
        status=HelpRequest.STATUS_PENDING
    )
    db.session.add(help_request)
    db.session.commit()
    
    # Notify admin
    from ...realtime import notify_admin_help_requested
    notify_admin_help_requested(help_request, professional, ticket)
    
    return jsonify({
        'success': True,
        'message': "Help request submitted for admin approval",
        'help_request_id': help_request.id
    })


# Chat Endpoints

@professional_bp.route('/api/chat/history', methods=['GET'])
@professional_login_required
def get_chat_history():
    """Get chat history with admin."""
    professional = Professional.query.get(session['professional_id'])
    
    # Get messages where professional is sender or receiver
    messages = ChatMessage.query.filter(
        ((ChatMessage.sender_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & 
         (ChatMessage.sender_id == professional.id)) |
        ((ChatMessage.receiver_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & 
         (ChatMessage.receiver_id == professional.id))
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    return jsonify({
        'success': True,
        'messages': [msg.to_dict() for msg in messages]
    })


@professional_bp.route('/api/chat/send', methods=['POST'])
@professional_login_required
def send_chat_message():
    """Send a chat message to admin."""
    professional = Professional.query.get(session['professional_id'])
    
    data = request.get_json()
    message_text = data.get('message', '').strip()
    
    if not message_text:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400
    
    try:
        # Find an admin to send to (first available admin)
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            return jsonify({'success': False, 'error': 'No admin available'}), 400
        
        chat_message = ChatMessage(
            sender_type=ChatMessage.SENDER_TYPE_PROFESSIONAL,
            sender_id=professional.id,
            receiver_type=ChatMessage.SENDER_TYPE_ADMIN,
            receiver_id=admin.id,
            message=message_text
        )
        db.session.add(chat_message)
        db.session.commit()
        
        # Emit via WebSocket
        from ...realtime import emit_chat_message
        emit_chat_message(chat_message)
        
        return jsonify({
            'success': True,
            'message': 'Message sent successfully',
            'chat_message': chat_message.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@professional_bp.route('/api/task/<int:ticket_id>')
@professional_login_required
@handle_api_errors
def get_task_detail_api(ticket_id):
    """Get task details via API."""
    professional = Professional.query.get(session['professional_id'])
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if ticket.assigned_professional_id != professional.id:
        return jsonify({
            'success': False,
            'error': "Not authorized"
        }), 403
    return jsonify({
        'success': True,
        'ticket': ticket.to_dict()
    })


@professional_bp.route('/api/chat/reset', methods=['POST'])
@professional_login_required
@handle_api_errors
def reset_chat_history():
    """Clear chat history for the current professional."""
    prof_id = session['professional_id']
    ChatMessage.query.filter(
        ((ChatMessage.sender_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & (ChatMessage.sender_id == prof_id)) |
        ((ChatMessage.receiver_type == ChatMessage.SENDER_TYPE_PROFESSIONAL) & (ChatMessage.receiver_id == prof_id))
    ).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': "Chat history reset successfully"
    })
