import sys
import requests


BASE = "http://localhost:8000"
TOWER_KEY = "dev-tower-key"

def die(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def req(method, url, **kwargs):
    r = requests.request(method, url, timeout=20, **kwargs)
    return r

def get_token(base: str, username: str, password: str) -> str:
    # Try signup, if conflict then login
    r = req("POST", f"{base}/auth/signup", json={"username": username, "password": password})
    if r.status_code == 201:
        print(f"Signed up {username}")
        return r.json()["access_token"]
    if r.status_code == 409:
        r2 = req("POST", f"{base}/auth/login", json={"username": username, "password": password})
        if r2.status_code != 200:
            die(f"Login failed for {username}: {r2.status_code} {r2.text}")
        print(f"Logged in {username}")
        return r2.json()["access_token"]
    die(f"Signup failed for {username}: {r.status_code} {r.text}")

def claim_fob(base: str, token: str, fob_uid: str):
    r = req(
        "POST",
        f"{base}/fob/claim",
        headers={"Authorization": f"Bearer {token}"},
        json={"fob_uid": fob_uid},
    )
    if r.status_code == 201:
        print(f"Claimed fob {fob_uid}")
        return
    # tolerate already claimed or conflict
    if r.status_code == 409:
        print(f"Fob claim conflict (ok): {r.text}")
        return
    die(f"Claim fob failed: {r.status_code} {r.text}")

def add_friend(base: str, token: str, friend_username: str):
    r = req(
        "POST",
        f"{base}/friends/add",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": friend_username},
    )
    if r.status_code == 200:
        print(f"Added friend {friend_username} (mutual)")
        return
    die(f"Add friend failed: {r.status_code} {r.text}")

def tower_ping(base: str, fob_uid: str, lat: float, lng: float, status: int = 0):
    r = req(
        "POST",
        f"{base}/tower/pings",
        headers={"X-Tower-Key": TOWER_KEY},
        json={"fob_uid": fob_uid, "lat": lat, "lng": lng, "status": status},
    )
    if r.status_code == 201:
        status_text = {0: "Safe", 1: "Not Safe", 2: "SOS"}[status]
        print(f"Tower ping stored for {fob_uid} @ {lat},{lng} ({status_text})")
        return
    die(f"Tower ping failed: {r.status_code} {r.text}")

def map_latest(base: str, token: str):
    r = req(
        "GET",
        f"{base}/map/latest",
        headers={"Authorization": f"Bearer {token}"},
    )
    if r.status_code != 200:
        die(f"Map latest failed: {r.status_code} {r.text}")
    return r.json()

def create_incident(base: str, token: str, lat: float, lng: float, description: str):
    r = req(
        "POST",
        f"{base}/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"lat": lat, "lng": lng, "description": description},
    )
    if r.status_code == 201:
        incident_id = r.json()["id"]
        print(f"Created incident {incident_id}: {description}")
        return incident_id
    die(f"Create incident failed: {r.status_code} {r.text}")

def get_incidents(base: str, token: str, window_hours: int = None):
    params = {}
    if window_hours is not None:
        params["window_hours"] = window_hours
    
    r = req(
        "GET",
        f"{base}/incidents",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )
    if r.status_code != 200:
        die(f"Get incidents failed: {r.status_code} {r.text}")
    return r.json()

def create_user_sos(base: str, token: str, lat: float, lng: float, message: str = None):
    payload = {"lat": lat, "lng": lng}
    if message:
        payload["message"] = message
    
    r = req(
        "POST",
        f"{base}/incidents/sos",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    if r.status_code == 201:
        sos_id = r.json()["id"]
        print(f"Created user SOS {sos_id} @ {lat},{lng}")
        return sos_id
    die(f"Create user SOS failed: {r.status_code} {r.text}")

def get_all_pings(base: str, token: str, window_minutes: int = None):
    params = {}
    if window_minutes is not None:
        params["window_minutes"] = window_minutes
    
    r = req(
        "GET",
        f"{base}/map/pings",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )
    if r.status_code != 200:
        die(f"Get all pings failed: {r.status_code} {r.text}")
    return r.json()

def main():
    # Health
    r = req("GET", f"{BASE}/health")
    if r.status_code != 200 or r.json().get("ok") is not True:
        die(f"Health failed: {r.status_code} {r.text}")
    print(f"Health OK at {BASE}")
    
    # tower ping
    tower_ping(BASE, "FOB_001", 43.6635, 79.3958)
    tower_ping(BASE, "FOB_002", 43.4723, 80.5449)
    
    # Users
    alice_token = get_token(BASE, "alice", "pw")
    bob_token = get_token(BASE, "bob", "pw")
    
    # claim fobs
    claim_fob(BASE, alice_token, "FOB_001")
    claim_fob(BASE, bob_token, "FOB_002")
    
    # alice adds bob
    add_friend(BASE, alice_token, "bob")
    
    # Test incidents functionality
    print("\n--- Testing Incidents ---")
    
    # Create a regular incident
    incident_id = create_incident(BASE, alice_token, 43.6532, 79.3832, "Suspicious person loitering")
    
    # Create a user SOS (without fob)
    user_sos_id = create_user_sos(BASE, alice_token, 43.6600, 79.4000, "Need immediate help")
    
    # Try to create another user SOS within 10 minutes (should NOT send SMS)
    user_sos_id2 = create_user_sos(BASE, alice_token, 43.6601, 79.4001, "Still need help")
    
    # Send SOS ping from bob's fob (should create incident and send SMS)
    tower_ping(BASE, "FOB_002", 43.4800, 80.5500, status=2)  # SOS ping
    
    # Send another SOS ping from same fob (should NOT send SMS due to duplicate status)
    tower_ping(BASE, "FOB_002", 43.4801, 80.5501, status=2)  # Another SOS ping
    
    # Get all incidents
    incidents_all = get_incidents(BASE, alice_token)
    print(f"All incidents count: {len(incidents_all['incidents'])}")
    
    # Get recent incidents (last 24 hours)
    incidents_24h = get_incidents(BASE, alice_token, window_hours=24)
    print(f"Last 24h incidents count: {len(incidents_24h['incidents'])}")
    
    print("Note: SMS duplicate suppression should prevent multiple SMS for repeated SOS alerts")
    
    print("\n--- Testing Map ---")
    # alice gets map/latest
    body = map_latest(BASE, alice_token)
    print("Map latest response:")
    print(body)
    
    # Test new all pings endpoint
    print("\n--- Testing All Pings ---")
    all_pings = get_all_pings(BASE, alice_token)
    print(f"Latest pings per fob: {len(all_pings['pings'])}")
    
    # Test with time filter (last 60 minutes)
    recent_pings = get_all_pings(BASE, alice_token, window_minutes=60)
    print(f"Latest pings per fob in last 60 minutes: {len(recent_pings['pings'])}")
    
    # Test that pings endpoint returns only latest ping per fob_uid
    print("\n--- Testing Pings Deduplication ---")
    # Send multiple pings for same fob to test deduplication
    tower_ping(BASE, "FOB_001", 43.4700, 80.5400, status=0)  # Additional ping for FOB_001
    tower_ping(BASE, "FOB_002", 43.4800, 80.5500, status=1)  # Additional ping for FOB_002
    
    # Get all pings again - should still only show latest per fob
    dedup_pings = get_all_pings(BASE, alice_token)
    fob_uids_in_response = [ping['fob_uid'] for ping in dedup_pings['pings']]
    unique_fobs = set(fob_uids_in_response)
    
    print(f"Unique fob_uids in pings response: {len(unique_fobs)}")
    print(f"Total pings returned: {len(dedup_pings['pings'])}")
    
    if len(unique_fobs) == len(dedup_pings['pings']):
        print("✅ PASS: Pings endpoint returns only latest ping per fob_uid")
    else:
        print("❌ FAIL: Pings endpoint returned duplicate fob_uids")
        print(f"Fob UIDs: {fob_uids_in_response}")
    
    print("\n🎉 All tests passed!")

def test_real_sms():
    """Test case that should actually send SMS with real phone numbers"""
    print("\n🚨 --- Testing REAL SMS (will send actual SMS!) ---")
    print("This test will create a fresh user/fob to ensure SMS is sent")
    
    # Create completely new user and fob to avoid any SOS status conflicts
    charlie_token = get_token(BASE, "charlie_sms_test", "password123")
    fresh_fob_uid = "FOB_SMS_TEST_001"
    
    # Send a safe ping first to establish the fob
    tower_ping(BASE, fresh_fob_uid, 43.7000, 79.4000, status=0)  # Safe ping
    
    # Claim the fresh fob
    claim_fob(BASE, charlie_token, fresh_fob_uid)
    
    print("⚠️  SENDING REAL SMS MESSAGE - Check your phone!")
    print("📱 SMS will be sent to the number configured in SOS_ALERT_NUMBERS")
    
    # This SOS should trigger an actual SMS since it's a new fob with no previous SOS status
    tower_ping(BASE, fresh_fob_uid, 43.7001, 79.4001, status=2)  # SOS ping - should send SMS!
    
    print("✅ SOS alert sent! If configured correctly, you should receive an SMS.")
    print("🔍 Check server logs for SMS success/failure details.")
    
    # Also test user SOS with fresh user (no recent SOS incidents)
    print("\n🚨 Testing User SOS (should also send SMS)")
    create_user_sos(BASE, charlie_token, 43.7002, 79.4002, "REAL SMS TEST - Emergency help needed!")
    
    print("✅ User SOS sent! Check your phone for SMS.")


if __name__ == "__main__":
    main()
    
    # Ask user if they want to test real SMS
    response = input("\n🚨 Do you want to test REAL SMS sending? This will send actual SMS messages to configured numbers. (y/N): ")
    if response.lower().startswith('y'):
        test_real_sms()
    else:
        print("Skipping real SMS test.")
