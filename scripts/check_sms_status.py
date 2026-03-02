#!/usr/bin/env python3
"""
Script to check the delivery status of SMS messages sent via Twilio.
Usage: python scripts/check_sms_status.py <message_sid>
"""

import sys
import os
from twilio.rest import Client

def check_sms_status(message_sid: str):
    """Check the delivery status of an SMS message."""
    
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("❌ ERROR: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables must be set")
        return
        
    try:
        client = Client(account_sid, auth_token)
        message = client.messages(message_sid).fetch()
        
        print(f"📱 SMS Status Report for SID: {message_sid}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Status: {message.status}")
        print(f"To: {message.to}")
        print(f"From: {message.from_}")
        print(f"Price: {message.price} {message.price_unit}" if message.price else "Price: Not available")
        print(f"Direction: {message.direction}")
        print(f"Date Created: {message.date_created}")
        print(f"Date Sent: {message.date_sent}")
        print(f"Date Updated: {message.date_updated}")
        
        if message.error_code:
            print(f"❌ Error Code: {message.error_code}")
            print(f"❌ Error Message: {message.error_message}")
        
        # Status explanations
        status_explanations = {
            'queued': '⏳ Message is queued and will be sent shortly',
            'sent': '✅ Message was sent to carrier',
            'delivered': '✅ Message was delivered to recipient',
            'undelivered': '❌ Message delivery failed - often due to invalid number or carrier blocking',
            'failed': '❌ Message failed to send - check number format and account status'
        }
        
        explanation = status_explanations.get(message.status, "Unknown status")
        print(f"\nExplanation: {explanation}")
        
        if message.status == 'sent':
            print("\n📋 TROUBLESHOOTING TIPS:")
            print("• Message was sent successfully but shows 'sent' not 'delivered'")
            print("• This often means the carrier accepted it but may have filtered it")
            print("• Check iPhone 'Filter Unknown Senders' in Messages app") 
            print("• Check Do Not Disturb/Focus mode settings")
            print("• Try sending a test SMS from a different number to this phone")
            
        elif message.status == 'undelivered':
            print("\n📋 TROUBLESHOOTING TIPS:")
            print("• Message was rejected by carrier - likely due to spam filtering")
            print("• Try using less 'alert-like' language in messages") 
            print("• Consider using a verified sender ID/short code")
            print("• Contact Twilio support if this persists")
            
    except Exception as e:
        print(f"❌ Error checking message status: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_sms_status.py <message_sid>")
        print("Example: python scripts/check_sms_status.py SM8ed6fdf6f5c89e29bc0e5af2bac18cf7")
        sys.exit(1)
    
    message_sid = sys.argv[1]
    check_sms_status(message_sid)