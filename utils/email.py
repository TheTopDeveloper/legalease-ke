"""
Email utilities for the system.
Handles sending various system emails including invitations, notifications, etc.
"""
import os
import logging
from smtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logger = logging.getLogger(__name__)

# Email configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
DEFAULT_SENDER = os.environ.get('DEFAULT_SENDER', 'noreply@kenyalegalassistant.com')
DEVELOPMENT_MODE = os.environ.get('FLASK_ENV', 'development') == 'development'

def send_email(to_email, subject, html_content, text_content=None):
    """
    Send an email with both HTML and plain text versions.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML version of the email content
        text_content: Plain text version of the email content (optional)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # If in development mode, just log the email
    if DEVELOPMENT_MODE or not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        logger.info(f"Development mode: Email would be sent to {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Content: {html_content}")
        return True

    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = DEFAULT_SENDER
    msg['To'] = to_email
    
    # Create the plain text version if not provided
    if text_content is None:
        text_content = html_content.replace('<br>', '\n').replace('</p>', '\n\n')
        # Basic HTML tag removal - can be enhanced with a proper library
        import re
        text_content = re.sub(r'<[^>]*>', '', text_content)
    
    # Attach parts
    part1 = MIMEText(text_content, 'plain')
    part2 = MIMEText(html_content, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        # Connect to server
        server = SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(DEFAULT_SENDER, to_email, msg.as_string())
        server.close()
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except SMTPException as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
        return False

def send_invitation_email(to_email, password, organization_name, inviter_name):
    """
    Send organization invitation email.
    
    Args:
        to_email: Recipient email address
        password: Generated password for new account
        organization_name: Name of the organization
        inviter_name: Name of the person who sent the invitation
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"Invitation to join {organization_name} on Kenya Legal Assistant"
    
    html_content = f"""
    <h2>Welcome to Kenya Legal Assistant!</h2>
    <p>You've been invited by <strong>{inviter_name}</strong> to join <strong>{organization_name}</strong> 
    on the Kenya Legal Assistant platform.</p>
    
    <p>Here are your login credentials:</p>
    <ul>
        <li><strong>Email:</strong> {to_email}</li>
        <li><strong>Password:</strong> {password}</li>
    </ul>
    
    <p>Please log in at <a href="https://kenyalegalassistant.com/login">https://kenyalegalassistant.com/login</a> 
    and change your password as soon as possible.</p>
    
    <p>Kenya Legal Assistant is a comprehensive legal technology platform designed for 
    the Kenyan legal ecosystem, offering case management, legal research, document generation, 
    and more.</p>
    
    <p>If you have any questions, please reply to this email or contact support.</p>
    
    <p>Best regards,<br>
    The Kenya Legal Assistant Team</p>
    """
    
    return send_email(to_email, subject, html_content)