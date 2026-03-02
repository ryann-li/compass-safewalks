#!/usr/bin/env python3
"""
Test SMS delivery to verify carrier blocking issues are resolved.
Usage: python scripts/test_sms.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.sms import send_test_sms, check_sms_delivery_status

def test_sms_delivery():
    """Test SMS delivery with carrier-friendly message."""
    
    phone_number = "+17807101344"  # Your phone number
    
    print("📱 Testing SMS Delivery")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Sending test SMS to: {phone_number}")
    
    # Send test message
    result = send_test_sms(phone_number, "SafeWalks test - reply OK if you get this")
    
    if result["success"]:
        print(f"✅ Test SMS sent successfully!")
        print(f"📋 Message SID: {result['sid']}")
        print(f"📋 Initial Status: {result['status']}")
        
        print("\n⏳ Waiting 10 seconds to check delivery status...")
        import time
        time.sleep(10)
        
        # Check delivery status
        print("\n📊 Checking delivery status...")
        status = check_sms_delivery_status(result['sid'])
        
        if 'status' in status:
            print(f"📋 Final Status: {status['status']}")
            
            if status['status'] == 'delivered':
                print("🎉 SUCCESS: Message was delivered!")
            elif status['status'] == 'sent':
                print("⚠️  Message was sent but not confirmed delivered")
                print("   Check iPhone 'Filter Unknown Senders' in Messages app")
            elif status['status'] == 'failed':
                print(f"❌ Message failed: {status.get('error_message', 'Unknown error')}")
                print(f"   Error code: {status.get('error_code', 'N/A')}")
        
    else:
        print(f"❌ Failed to send test SMS: {result['error']}")
        
    print("\n📱 Next Steps:")
    print("1. Check your iPhone Messages app")
    print("2. Look in 'Filter Unknown Senders' section")
    print("3. Add SafeWalks number to contacts if found")
    print("4. Reply 'OK' if you received the message")

if __name__ == "__main__":
    test_sms_delivery()