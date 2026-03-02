import logging
from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioException

from .settings import get_settings

logger = logging.getLogger("compass.sms")


def check_sms_delivery_status(message_sid: str) -> dict:
    """
    Check the delivery status of an SMS message.
    
    Args:
        message_sid: Twilio message SID to check
        
    Returns:
        dict: Message status information
    """
    settings = get_settings()
    
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("SMS: Twilio credentials not configured")
        return {"error": "No Twilio credentials"}
        
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages(message_sid).fetch()
        
        status_info = {
            "sid": message.sid,
            "status": message.status,
            "error_code": message.error_code,
            "error_message": message.error_message,
            "price": message.price,
            "date_created": str(message.date_created),
            "date_sent": str(message.date_sent),
            "date_updated": str(message.date_updated),
            "to": message.to,
            "from_": message.from_
        }
        
        logger.info(f"SMS Status for {message_sid}: {status_info}")
        return status_info
        
    except Exception as e:
        logger.error(f"SMS: Error checking message status: {e}")
        return {"error": str(e)}


def send_test_sms(phone_number: str, message: str = "SafeWalks test message - please reply OK if received") -> dict:
    """
    Send a test SMS to verify delivery and avoid carrier blocking.
    
    Args:
        phone_number: Phone number to send test to
        message: Test message content
        
    Returns:
        dict: Result with success status and message SID or error
    """
    settings = get_settings()
    
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return {"success": False, "error": "Twilio credentials not configured"}
        
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message_instance = client.messages.create(
            body=message,
            from_=settings.TWILIO_FROM_NUMBER,
            to=phone_number
        )
        
        logger.info(f"Test SMS sent to {phone_number}, SID: {message_instance.sid}")
        return {
            "success": True,
            "sid": message_instance.sid,
            "status": message_instance.status
        }
        
    except Exception as e:
        logger.error(f"Failed to send test SMS: {e}")
        return {"success": False, "error": str(e)}


def send_sos_sms(
    user_info: str,
    lat: float,
    lng: float,
    message: Optional[str] = None,
    alert_type: str = "SOS"
) -> tuple[bool, list[str]]:
    """
    Send SOS alert SMS to configured emergency contacts.
    
    Args:
        user_info: User identification (username, ID, etc.)
        lat: Latitude coordinate
        lng: Longitude coordinate 
        message: Optional additional message
        alert_type: Type of alert (SOS, FOB SOS, etc.)
    
    Returns:
        tuple: (success: bool, message_sids: list[str])
    """
    settings = get_settings()
    
    # Skip SMS if Twilio credentials are not configured
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("SMS: Twilio credentials not configured, skipping SMS")
        return False, []
        
    if not settings.SOS_ALERT_NUMBERS:
        logger.warning("SMS: No SOS alert phone numbers configured, skipping SMS")
        return False, []

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Construct SMS message with carrier-friendly language that still conveys urgency
        sms_body = f"SafeWalks - User Needs Help\n"
        sms_body += f"User: {user_info}\n"
        sms_body += f"Location: {lat}, {lng}\n"
        sms_body += f"Map: https://maps.google.com/maps?q={lat},{lng}\n"
        
        if message and message.strip():
            sms_body += f"Message: {message}\n"
        else:
            sms_body += f"Message: No message provided\n"
        
        sms_body += f"\nType: {alert_type}\nPlease check on this person"
        
        # Send SMS to all configured numbers
        success_count = 0
        message_sids = []
        for phone_number in settings.SOS_ALERT_NUMBERS:
            try:
                message_instance = client.messages.create(
                    body=sms_body,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=phone_number
                )
                logger.info(f"SMS sent to {phone_number}, SID: {message_instance.sid}")
                message_sids.append(message_instance.sid)
                success_count += 1
            except TwilioException as e:
                logger.error(f"SMS: Failed to send SMS to {phone_number}: {e}")
        
        if success_count > 0:
            logger.info(f"SOS SMS sent to {success_count}/{len(settings.SOS_ALERT_NUMBERS)} numbers")
            return True, message_sids
        else:
            logger.error("SMS: Failed to send SMS to any configured numbers")
            return False, []
            
    except Exception as e:
        logger.error(f"SMS: Unexpected error sending SOS SMS: {e}")
        return False, []