import os
import requests
import json
import logging

# ==============================================================================
# Load from .env / environment variables
EMAILJS_SERVICE_ID = os.environ.get('EMAILJS_SERVICE_ID', '')
EMAILJS_TEMPLATE_ID = os.environ.get('EMAILJS_TEMPLATE_ID', '')
EMAILJS_PUBLIC_KEY = os.environ.get('EMAILJS_PUBLIC_KEY', '')
EMAILJS_PRIVATE_KEY = os.environ.get('EMAILJS_PRIVATE_KEY', '')
EMAILJS_API_URL = 'https://api.emailjs.com/api/v1.0/email/send'

logger = logging.getLogger(__name__)

def send_ticket_email(ticket, action='created'):
    """
    Sends an automated email notification using the EmailJS REST API.
    
    Args:
        ticket (Ticket): The ticket instance related to the notification.
        action (str): The action that triggered the email ('created', 'in-progress', 'fixed').
    """
    if not EMAILJS_SERVICE_ID or not EMAILJS_TEMPLATE_ID or not EMAILJS_PUBLIC_KEY:
        print(f"WARNING: EmailJS is not fully configured. Skipping email for Ticket #{ticket.id} ({action}).")
        return False

    # Customize the email message slightly based on the action
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

    # Prepare payload for EmailJS API
    # Ensure your EmailJS template expects variables like {{to_email}}, {{to_name}}, {{subject}}, and {{message}}
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
            print(f"SUCCESS: EmailJS successfully sent {action} email for Ticket #{ticket.id}")
            return True
        else:
            print(f"ERROR: Failed to send email via EmailJS for Ticket #{ticket.id}: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: Exception occurred while sending email for Ticket #{ticket.id}: {str(e)}")
        return False


def send_verification_email(email, name, verification_link):
    """
    Send an email verification link to a newly registered user using EmailJS.
    """
    if not EMAILJS_SERVICE_ID or not EMAILJS_TEMPLATE_ID or not EMAILJS_PUBLIC_KEY:
        print(f"WARNING: EmailJS is not fully configured. Skipping verification email for {email}.")
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
            'ticket_id': '-'  # Placeholder for template requirement
        }
    }

    try:
        response = requests.post(
            EMAILJS_API_URL, 
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            print(f"SUCCESS: EmailJS successfully sent verification email to {email}")
            return True
        else:
            print(f"ERROR: Failed to send verification email via EmailJS to {email}: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: Exception occurred while sending verification email to {email}: {str(e)}")
        return False


def send_password_reset_email(email, name, reset_link):
    """
    Send a password-reset link to a user using EmailJS.
    """
    if not EMAILJS_SERVICE_ID or not EMAILJS_TEMPLATE_ID or not EMAILJS_PUBLIC_KEY:
        print(f"WARNING: EmailJS not configured. Skipping reset email for {email}.")
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
            print(f"SUCCESS: Password reset email sent to {email}")
            return True
        else:
            print(f"ERROR: Failed to send reset email to {email}: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: Exception sending reset email to {email}: {str(e)}")
        return False
