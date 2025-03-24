import os
import logging
from utils.notification_service import TwilioSMSService, MockSMSService, TWILIO_AVAILABLE

# Configure logging
logger = logging.getLogger(__name__)

def send_twilio_message(to_phone_number: str, message: str) -> dict:
    """
    Send an SMS message using Twilio if available, otherwise use mock service
    
    Args:
        to_phone_number: Recipient phone number
        message: SMS message content
            
    Returns:
        Dict with success status and message ID
    """
    # Check if Twilio credentials are available
    twilio_creds_available = all([
        os.environ.get('TWILIO_ACCOUNT_SID'),
        os.environ.get('TWILIO_AUTH_TOKEN'),
        os.environ.get('TWILIO_PHONE_NUMBER')
    ])
    
    if TWILIO_AVAILABLE and twilio_creds_available:
        logger.info("Using Twilio SMS service for direct message")
        service = TwilioSMSService()
    else:
        logger.info("Using Mock SMS service for direct message (Twilio unavailable)")
        service = MockSMSService()
    
    # Ensure phone number is in international format for Kenya
    if not to_phone_number.startswith('+') and to_phone_number.startswith('0'):
        to_phone_number = '+254' + to_phone_number[1:]
    
    # Send the message
    result = service.send_sms(to_phone_number, message)
    
    if result.get('success', False):
        logger.info(f"Successfully sent message to {to_phone_number}")
    else:
        logger.error(f"Failed to send message to {to_phone_number}: {result.get('error', 'Unknown error')}")
    
    return result