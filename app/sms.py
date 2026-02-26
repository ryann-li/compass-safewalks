import logging
from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioException

from .settings import get_settings

logger = logging.getLogger("compass.sms")


def send_sos_sms(
    user_info: str,
    lat: float,
    lng: float,
    message: Optional[str] = None,
    alert_type: str = "SOS"
) -> bool:
    """
    Send SOS alert SMS to configured emergency contacts.
    
    Args:
        user_info: User identification (username, ID, etc.)
        lat: Latitude coordinate
        lng: Longitude coordinate 
        message: Optional additional message
        alert_type: Type of alert (SOS, FOB SOS, etc.)
    
    Returns:
        bool: True if SMS sent successfully, False otherwise
    """
    settings = get_settings()
    
    # Skip SMS if Twilio credentials are not configured
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials not configured, skipping SMS")
        return False
        
    if not settings.SOS_ALERT_NUMBERS:
        logger.warning("No SOS alert phone numbers configured, skipping SMS")
        return False

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Construct SMS message
        sms_body = f"🚨 {alert_type} ALERT\n"
        sms_body += f"User: {user_info}\n"
        sms_body += f"Location: {lat}, {lng}\n"
        sms_body += f"Maps: https://maps.google.com/maps?q={lat},{lng}\n"
        
        if message:
            sms_body += f"Message: {message}\n"
        
        sms_body += "\nIMMEDIATE RESPONSE REQUIRED"
        
        # Send SMS to all configured numbers
        success_count = 0
        for phone_number in settings.SOS_ALERT_NUMBERS:
            try:
                message_instance = client.messages.create(
                    body=sms_body,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=phone_number
                )
                logger.info(f"SMS sent to {phone_number}, SID: {message_instance.sid}")
                success_count += 1
            except TwilioException as e:
                logger.error(f"Failed to send SMS to {phone_number}: {e}")
        
        if success_count > 0:
            logger.info(f"SOS SMS sent to {success_count}/{len(settings.SOS_ALERT_NUMBERS)} numbers")
            return True
        else:
            logger.error("Failed to send SMS to any configured numbers")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error sending SOS SMS: {e}")
        return False