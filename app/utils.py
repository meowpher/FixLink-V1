"""
Shared utilities for FixLink - Consolidated from email_utils.py and file_utils.py.
Handles email notifications via EmailJS and file upload validations.
"""
import os
import requests
import json
import logging

# ==============================================================================
# Configuration
# ==============================================================================
EMAILJS_SERVICE_ID = os.environ.get('EMAILJS_SERVICE_ID', '')
EMAILJS_TEMPLATE_ID = os.environ.get('EMAILJS_TEMPLATE_ID', '')
EMAILJS_PUBLIC_KEY = os.environ.get('EMAILJS_PUBLIC_KEY', '')
EMAILJS_PRIVATE_KEY = os.environ.get('EMAILJS_PRIVATE_KEY', '')
EMAILJS_API_URL = 'https://api.emailjs.com/api/v1.0/email/send'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

logger = logging.getLogger(__name__)

# ==============================================================================
# File Utilities
# ==============================================================================

def allowed_file(filename):
    """Return True if *filename* has an allowed image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==============================================================================
# Email Utilities
# ==============================================================================

def send_ticket_email(ticket, action='created'):
    """
    Sends an automated email notification using the EmailJS REST API.
    """
    if not EMAILJS_SERVICE_ID or not EMAILJS_TEMPLATE_ID or not EMAILJS_PUBLIC_KEY:
        logger.warning(f"EmailJS is not fully configured. Skipping email for Ticket #{ticket.id} ({action}).")
        return False

    subject = f"FixLink Ticket #{ticket.id} "
    if action == 'created':
        subject += "Received"
        message = f"Hello {ticket.reporter_name},\n\nYour maintenance request for room {ticket.room.number} regarding {ticket.issue_type} has been received. We will look into it shortly."
    elif action == 'in-progress':
        subject += "is In-Progress"
        message = f"Hello {ticket.reporter_name},\n\nYour maintenance request for room {ticket.room.number} is now being worked on by our team."
    elif action == 'fixed':
        subject += "is Fixed!"
        message = f"Hello {ticket.reporter_name},\n\nGood news! Your maintenance request for room {ticket.room.number} has been resolved. Thank you for using FixLink!"
    else:
        subject += "Update"
        message = f"Hello {ticket.reporter_name},\n\nThere is an update on your ticket #{ticket.id}. Its current status is: {ticket.status}."

    payload = {
        'service_id': EMAILJS_SERVICE_ID,
        'template_id': EMAILJS_TEMPLATE_ID,
        'user_id': EMAILJS_PUBLIC_KEY,
        'accessToken': EMAILJS_PRIVATE_KEY,
        'template_params': {
            'to_email': ticket.reporter_email,
            'to_name': ticket.reporter_name,
            'ticket_id': str(ticket.id),
            'subject': subject,
            'message': message,
        }
    }

    try:
        response = requests.post(
            EMAILJS_API_URL, 
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            logger.info(f"SUCCESS: EmailJS successfully sent {action} email for Ticket #{ticket.id}")
            return True
        else:
            logger.error(f"ERROR: Failed to send email via EmailJS for Ticket #{ticket.id}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"ERROR: Exception occurred while sending email for Ticket #{ticket.id}: {str(e)}")
        return False


def send_verification_email(email, name, verification_link):
    """
    Send an email verification link to a newly registered user using EmailJS.
    """
    if not EMAILJS_SERVICE_ID or not EMAILJS_TEMPLATE_ID or not EMAILJS_PUBLIC_KEY:
        logger.warning(f"EmailJS is not fully configured. Skipping verification email for {email}.")
        return False

    message = f"""
    Hello {name},
    
    Please verify your email address and set your password by clicking the link below:
    
    {verification_link}
    
    If you did not request this, please ignore this email.
    
    Regards,
    MIT-WPU Smart-Room Maintenance Team
    """

    payload = {
        'service_id': EMAILJS_SERVICE_ID,
        'template_id': EMAILJS_TEMPLATE_ID,
        'user_id': EMAILJS_PUBLIC_KEY,
        'accessToken': EMAILJS_PRIVATE_KEY,
        'template_params': {
            'to_email': email,
            'to_name': name,
            'subject': 'Verify Your MIT-WPU FixLink Account',
            'message': message,
            'ticket_id': '-'
        }
    }

    try:
        response = requests.post(
            EMAILJS_API_URL, 
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            logger.info(f"SUCCESS: EmailJS successfully sent verification email to {email}")
            return True
        else:
            logger.error(f"ERROR: Failed to send verification email via EmailJS to {email}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"ERROR: Exception occurred while sending verification email to {email}: {str(e)}")
        return False


def send_password_reset_email(email, name, reset_link):
    """
    Send a password-reset link to a user using EmailJS.
    """
    if not EMAILJS_SERVICE_ID or not EMAILJS_TEMPLATE_ID or not EMAILJS_PUBLIC_KEY:
        logger.warning(f"EmailJS not configured. Skipping reset email for {email}.")
        return False

    message = f"""
    Hello {name},

    You requested a password reset for your MIT-WPU FixLink account.
    Click the link below to set a new password:

    {reset_link}

    This link expires in 1 hour. If you did not request this, ignore this email.

    Regards,
    MIT-WPU Smart-Room Maintenance Team
    """

    payload = {
        'service_id': EMAILJS_SERVICE_ID,
        'template_id': EMAILJS_TEMPLATE_ID,
        'user_id': EMAILJS_PUBLIC_KEY,
        'accessToken': EMAILJS_PRIVATE_KEY,
        'template_params': {
            'to_email': email,
            'to_name': name,
            'subject': 'Reset Your MIT-WPU FixLink Password',
            'message': message,
            'ticket_id': '-'
        }
    }

    try:
        response = requests.post(
            EMAILJS_API_URL,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            logger.info(f"SUCCESS: Password reset email sent to {email}")
            return True
        else:
            logger.error(f"ERROR: Failed to send reset email to {email}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"ERROR: Exception sending reset email to {email}: {str(e)}")
        return False

# ==============================================================================
# Web Push Utilities
# ==============================================================================

def send_web_push(user_id=None, professional_id=None, title="New Notification", body="", url="/"):
    """
    Sends a Web Push notification to a specific user or professional using pywebpush.
    """
    try:
        from pywebpush import webpush, WebPushException
        from .models import PushSubscription
        
        vapid_private_key = os.environ.get('VAPID_PRIVATE_KEY')
        vapid_claims = {"sub": os.environ.get('VAPID_SUBJECT', 'mailto:admin@fixlink.edu')}
        
        if not vapid_private_key:
            logger.warning("VAPID_PRIVATE_KEY not found. Skipping Web Push dispatch.")
            return False
            
        subs = []
        if user_id:
            subs = PushSubscription.query.filter_by(user_id=user_id).all()
        elif professional_id:
            subs = PushSubscription.query.filter_by(professional_id=professional_id).all()
            
        success = True
        for sub in subs:
            try:
                webpush(
                    subscription_info=sub.to_dict(),
                    data=json.dumps({"title": title, "body": body, "url": url}),
                    vapid_private_key=vapid_private_key,
                    vapid_claims=vapid_claims
                )
            except WebPushException as ex:
                logger.error(f"WebPushException: {repr(ex)}")
                # If Gone (unsubscribed), remove from DB
                if ex.response and ex.response.status_code == 410:
                    from . import db
                    db.session.delete(sub)
                    db.session.commit()
                success = False
        return success
    except Exception as e:
        logger.error(f"Failed to trigger web push: {e}")
        return False
