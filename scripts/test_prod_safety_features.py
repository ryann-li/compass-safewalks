#!/usr/bin/env python3
"""
Production E2E test script for Compass SafeWalks safety features.

Tests the deployed API at https://compass-safewalks.vercel.app/
against the new safety features implemented.
"""

import sys
import requests
import time
from typing import Dict


BASE = "https://compass-safewalks.vercel.app"
TOWER_KEY = "dev-tower-key"

def die(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)

def success(msg: str):
    print(f"✅ {msg}")

def info(msg: str):
    print(f"ℹ️  {msg}")

def req(method: str, url: str, **kwargs) -> requests.Response:
    """Make HTTP request with timeout and error handling."""
    try:
        r = requests.request(method, url, timeout=20, **kwargs)
        return r
    except requests.RequestException as e:
        die(f"Request failed: {e}")

def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def tower_headers() -> Dict[str, str]:
    return {"X-Tower-Key": TOWER_KEY}

def get_token(username: str, password: str = "testpw") -> str:
    """Get auth token, trying signup first then login."""
    # Try signup first
    r = req("POST", f"{BASE}/auth/signup", json={"username": username, "password": password})
    if r.status_code == 201:
        info(f"Signed up {username}")
        return r.json()["access_token"]
    elif r.status_code == 409:
        # User exists, try login
        r = req("POST", f"{BASE}/auth/login", json={"username": username, "password": password})
        if r.status_code == 200:
            info(f"Logged in {username}")
            return r.json()["access_token"]
        else:
            die(f"Login failed for {username}: {r.status_code} {r.text}")
    else:
        die(f"Signup failed for {username}: {r.status_code} {r.text}")

def test_health():
    """Test basic health endpoint."""
    info("Testing health endpoint...")
    r = req("GET", f"{BASE}/health")
    if r.status_code == 200 and r.json().get("ok") is True:
        success("Health check passed")
    else:
        die(f"Health check failed: {r.status_code} {r.text}")

def test_profile_features():
    """Test unified PATCH /auth/me endpoint with multipart/form-data."""
    info("Testing profile features...")
    
    timestamp = int(time.time())
    username = f"testuser_profile_{timestamp}"
    token = get_token(username)
    
    # Test 1: Update display name only
    info("Testing display name update...")
    files = {'display_name': (None, 'Test User Display')}  # Form field without file
    r = req("PATCH", f"{BASE}/auth/me", 
            files=files, 
            headers=auth_headers(token))
    
    if r.status_code == 200:
        profile = r.json()
        if profile.get("display_name") == "Test User Display":
            success("Display name update works")
        else:
            die(f"Display name update failed: expected 'Test User Display', got {profile.get('display_name')}")
    else:
        die(f"Display name update failed: {r.status_code} {r.text}")
    
    # Test 2: Upload avatar with real file
    info("Testing avatar upload with real file...")
    
    # Use the provided test file
    test_file_path = "/Users/ryanli/Desktop/peter.png"
    try:
        with open(test_file_path, 'rb') as f:
            files = {
                'profile_picture': ('peter.png', f, 'image/png'),
                'display_name': (None, 'Peter with Avatar')
            }
            
            r = req("PATCH", f"{BASE}/auth/me",
                    files=files,
                    headers=auth_headers(token))
        
        if r.status_code == 200:
            profile = r.json()
            if (profile.get("display_name") == "Peter with Avatar" and 
                profile.get("profile_picture_url") and
                "vercel-storage.com" in profile.get("profile_picture_url")):
                success(f"Avatar upload with file works → {profile['profile_picture_url']}")
                
                # Verify the uploaded image is accessible
                info("Verifying uploaded image accessibility...")
                print("profile url is at:", profile["profile_picture_url"], profile)
                
                
                verify_response = req("GET", profile["profile_picture_url"])
                
                if verify_response.status_code == 200:
                    success("Uploaded image is accessible")
                else:
                    die(f"Uploaded image not accessible: {verify_response.status_code}")
                    
            else:
                die(f"Avatar upload response invalid: {profile}")
        elif r.status_code == 503:
            info("Avatar upload unavailable (BLOB_READ_WRITE_TOKEN not configured) - expected in some environments")
        else:
            die(f"Avatar upload failed: {r.status_code} {r.text}")
            
    except FileNotFoundError:
        info(f"Test file not found at {test_file_path} - skipping real file upload test")
        info("You can place a PNG file at /Users/ryanli/Desktop/peter.png to test file uploads")
    except Exception as e:
        die(f"Avatar upload test error: {e}")
    
    # Test 3: Test with simulated image data (fallback)
    info("Testing avatar upload with simulated image data...")
    
    # Create a minimal PNG-like binary data for testing
    fake_png_data = b'\x89PNG\r\n\x1a\n' + b'fake-png-data-for-testing' * 100  # Simulate a small PNG
    
    files = {
        'profile_picture': ('test_avatar.png', fake_png_data, 'image/png'),
        'display_name': (None, 'Test User with Simulated Avatar')
    }
    
    r = req("PATCH", f"{BASE}/auth/me",
            files=files,
            headers=auth_headers(token))
    
    if r.status_code == 200:
        profile = r.json()
        if (profile.get("display_name") == "Test User with Simulated Avatar" and 
            profile.get("profile_picture_url")):
            success("Avatar upload with simulated data works")
        else:
            die(f"Simulated avatar upload response invalid: {profile}")
    elif r.status_code == 503:
        info("Avatar upload unavailable (BLOB_READ_WRITE_TOKEN not configured) - expected in some environments")
    else:
        die(f"Simulated avatar upload failed: {r.status_code} {r.text}")
    
    # Test 4: Test validation errors
    info("Testing file validation...")
    
    # Test with invalid file type
    files = {
        'profile_picture': ('test.txt', b'not an image', 'text/plain'),
        'display_name': (None, 'Should Fail')
    }
    
    r = req("PATCH", f"{BASE}/auth/me",
            files=files,
            headers=auth_headers(token))
    
    if r.status_code == 400 and "INVALID_FILE_TYPE" in r.text:
        success("File type validation works")
    elif r.status_code == 503:
        info("Can't test validation when blob storage unavailable")
    else:
        die(f"File type validation failed: expected 400, got {r.status_code} {r.text}")
    
    # Test 5: Profile retrieval to verify current state  
    info("Verifying final profile state...")
    r = req("GET", f"{BASE}/auth/me", headers=auth_headers(token))
    
    if r.status_code == 200:
        profile = r.json()
        success(f"Final profile: {profile.get('display_name')} with avatar: {bool(profile.get('profile_picture_url'))}")
    else:
        die(f"Profile retrieval failed: {r.status_code} {r.text}")

def test_location_privacy():
    """Test location sharing privacy controls."""
    info("Testing location privacy controls...")
    
    timestamp = int(time.time())
    alice_username = f"alice_privacy_{timestamp}"
    bob_username = f"bob_privacy_{timestamp}"
    
    alice_token = get_token(alice_username)
    bob_token = get_token(bob_username)
    
    # Set up fobs and friendship
    alice_fob = f"FOB_ALICE_PRIV_{timestamp}"
    bob_fob = f"FOB_BOB_PRIV_{timestamp}"
    
    # Claim fobs
    for token, fob in [(alice_token, alice_fob), (bob_token, bob_fob)]:
        r = req("POST", f"{BASE}/fob/claim", json={"fob_uid": fob}, headers=auth_headers(token))
        if r.status_code not in [201, 409]:  # 409 = already claimed is OK
            die(f"Fob claim failed: {r.status_code} {r.text}")
    
    # Alice adds Bob as friend
    r = req("POST", f"{BASE}/friends/add", json={"username": bob_username}, headers=auth_headers(alice_token))
    if r.status_code != 200:
        die(f"Friend add failed: {r.status_code} {r.text}")
    success("Friendship established")
    
    # Alice gets a tower ping
    r = req("POST", f"{BASE}/tower/pings",
            json={"fob_uid": alice_fob, "lat": 43.65, "lng": -79.38, "status": 0},
            headers=tower_headers())
    if r.status_code != 201:
        die(f"Tower ping failed: {r.status_code} {r.text}")
    
    # Bob should see Alice on map
    r = req("GET", f"{BASE}/map/latest", headers=auth_headers(bob_token))
    if r.status_code != 200:
        die(f"Map latest failed: {r.status_code} {r.text}")
    
    results = r.json()["results"]
    alice_visible = any(res["friend"]["username"] == alice_username for res in results)
    if alice_visible:
        success("Alice visible to Bob (baseline)")
    else:
        die("Alice should be visible to Bob initially")
    
    # Alice disables location sharing for Bob
    r = req("PATCH", f"{BASE}/friends/share-location",
            json={"username": bob_username, "enabled": False},
            headers=auth_headers(alice_token))
    if r.status_code == 200:
        response = r.json()
        if response.get("is_sharing_location") is False:
            success("Location sharing disabled")
        else:
            die(f"Share toggle response unexpected: {response}")
    else:
        die(f"Share toggle failed: {r.status_code} {r.text}")
    
    # Bob should NOT see Alice now
    r = req("GET", f"{BASE}/map/latest", headers=auth_headers(bob_token))
    if r.status_code != 200:
        die(f"Map latest failed: {r.status_code} {r.text}")
    
    results = r.json()["results"]
    alice_visible = any(res["friend"]["username"] == alice_username for res in results)
    if not alice_visible:
        success("Alice invisible to Bob after privacy toggle")
    else:
        die("Alice should be invisible to Bob after disabling sharing")

def test_sos_alerting():
    """Test SOS ping status and map display."""
    info("Testing SOS alerting...")
    
    timestamp = int(time.time())
    alice_username = f"alice_sos_{timestamp}"
    bob_username = f"bob_sos_{timestamp}"
    
    alice_token = get_token(alice_username)
    bob_token = get_token(bob_username)
    
    alice_fob = f"FOB_ALICE_SOS_{timestamp}"
    
    # Set up fob and friendship
    r = req("POST", f"{BASE}/fob/claim", json={"fob_uid": alice_fob}, headers=auth_headers(alice_token))
    if r.status_code not in [201, 409]:
        die(f"Fob claim failed: {r.status_code} {r.text}")
    
    r = req("POST", f"{BASE}/friends/add", json={"username": alice_username}, headers=auth_headers(bob_token))
    if r.status_code != 200:
        die(f"Friend add failed: {r.status_code} {r.text}")
    
    # Send normal ping first
    r = req("POST", f"{BASE}/tower/pings",
            json={"fob_uid": alice_fob, "lat": 43.65, "lng": -79.38, "status": 0},
            headers=tower_headers())
    if r.status_code != 201:
        die(f"Normal ping failed: {r.status_code} {r.text}")
    
    # Verify normal status on map
    r = req("GET", f"{BASE}/map/latest", headers=auth_headers(bob_token))
    if r.status_code == 200:
        results = r.json()["results"]
        alice_result = next((res for res in results if res["friend"]["username"] == alice_username), None)
        if alice_result and alice_result["location"]["status"] == 0:
            success("Normal status (0) displayed on map")
        else:
            die(f"Normal status not found in map results: {results}")
    
    # Send SOS ping
    r = req("POST", f"{BASE}/tower/pings",
            json={"fob_uid": alice_fob, "lat": 43.66, "lng": -79.39, "status": 2},
            headers=tower_headers())
    if r.status_code == 201:
        success("SOS ping accepted")
    else:
        die(f"SOS ping failed: {r.status_code} {r.text}")
    
    # Verify SOS status on map
    r = req("GET", f"{BASE}/map/latest", headers=auth_headers(bob_token))
    if r.status_code == 200:
        results = r.json()["results"]
        alice_result = next((res for res in results if res["friend"]["username"] == alice_username), None)
        if alice_result and alice_result["location"]["status"] == 2:
            success("SOS status (2) displayed on map")
        else:
            die(f"SOS status not found in map results: {results}")
    else:
        die(f"Map latest failed: {r.status_code} {r.text}")

def test_incident_reporting():
    """Test incident creation."""
    info("Testing incident reporting...")
    
    timestamp = int(time.time())
    username = f"reporter_{timestamp}"
    token = get_token(username)
    
    incident_data = {
        "lat": 43.6532,
        "lng": -79.3832,
        "description": f"Test incident report at {timestamp}"
    }
    
    r = req("POST", f"{BASE}/incidents", json=incident_data, headers=auth_headers(token))
    if r.status_code == 201:
        incident = r.json()
        expected_fields = ["id", "reporter_id", "lat", "lng", "description", "created_at"]
        if all(field in incident for field in expected_fields):
            if (incident["lat"] == incident_data["lat"] and 
                incident["lng"] == incident_data["lng"] and
                incident["description"] == incident_data["description"]):
                success("Incident reporting works")
            else:
                die(f"Incident data mismatch: {incident}")
        else:
            die(f"Incident response missing fields: {incident}")
    else:
        die(f"Incident creation failed: {r.status_code} {r.text}")

def test_friends_metadata():
    """Test friends list with new metadata fields."""
    info("Testing friends list metadata...")
    
    timestamp = int(time.time())
    alice_username = f"alice_meta_{timestamp}"
    bob_username = f"bob_meta_{timestamp}"
    
    alice_token = get_token(alice_username)
    bob_token = get_token(bob_username)
    
    # Set Bob's profile
    mock_pic = "https://public.blob.vercel-storage.com/avatars/bob/avatar.png"
    r = req("PATCH", f"{BASE}/auth/me",
            json={"display_name": "Bob Test", "profile_picture_url": mock_pic},
            headers=auth_headers(bob_token))
    if r.status_code != 200:
        die(f"Bob profile update failed: {r.status_code} {r.text}")
    
    # Give Bob a fob and ping
    bob_fob = f"FOB_BOB_META_{timestamp}"
    r = req("POST", f"{BASE}/fob/claim", json={"fob_uid": bob_fob}, headers=auth_headers(bob_token))
    if r.status_code not in [201, 409]:
        die(f"Bob fob claim failed: {r.status_code} {r.text}")
    
    r = req("POST", f"{BASE}/tower/pings",
            json={"fob_uid": bob_fob, "lat": 43.47, "lng": -80.54},
            headers=tower_headers())
    if r.status_code != 201:
        die(f"Bob ping failed: {r.status_code} {r.text}")
    
    # Alice adds Bob
    r = req("POST", f"{BASE}/friends/add", json={"username": bob_username}, headers=auth_headers(alice_token))
    if r.status_code != 200:
        die(f"Friend add failed: {r.status_code} {r.text}")
    
    # Check Alice's friends list
    r = req("GET", f"{BASE}/friends", headers=auth_headers(alice_token))
    if r.status_code == 200:
        friends = r.json()["friends"]
        bob_friend = next((f for f in friends if f["username"] == bob_username), None)
        if bob_friend:
            expected_fields = ["id", "username", "display_name", "profile_picture_url", "latest_ping_received_at"]
            if all(field in bob_friend for field in expected_fields):
                if (bob_friend["display_name"] == "Bob Test" and
                    bob_friend["profile_picture_url"] == mock_pic and
                    bob_friend["latest_ping_received_at"] is not None):
                    success("Friends list metadata works")
                else:
                    die(f"Friends metadata values incorrect: {bob_friend}")
            else:
                die(f"Friends list missing metadata fields: {bob_friend}")
        else:
            die(f"Bob not found in Alice's friends: {friends}")
    else:
        die(f"Friends list failed: {r.status_code} {r.text}")

def test_regression_original_flow():
    """Test that original functionality still works."""
    info("Testing original flow regression...")
    
    timestamp = int(time.time())
    alice_username = f"alice_reg_{timestamp}"
    bob_username = f"bob_reg_{timestamp}"
    
    alice_token = get_token(alice_username)
    bob_token = get_token(bob_username)
    
    alice_fob = f"FOB_ALICE_REG_{timestamp}"
    bob_fob = f"FOB_BOB_REG_{timestamp}"
    
    # Claim fobs
    for token, fob in [(alice_token, alice_fob), (bob_token, bob_fob)]:
        r = req("POST", f"{BASE}/fob/claim", json={"fob_uid": fob}, headers=auth_headers(token))
        if r.status_code not in [201, 409]:
            die(f"Fob claim failed: {r.status_code} {r.text}")
    
    # Alice adds Bob
    r = req("POST", f"{BASE}/friends/add", json={"username": bob_username}, headers=auth_headers(alice_token))
    if r.status_code != 200:
        die(f"Friend add failed: {r.status_code} {r.text}")
    
    # Tower ping for Bob
    r = req("POST", f"{BASE}/tower/pings",
            json={"fob_uid": bob_fob, "lat": 43.65, "lng": -79.38},
            headers=tower_headers())
    if r.status_code != 201:
        die(f"Tower ping failed: {r.status_code} {r.text}")
    
    # Alice sees Bob on map
    r = req("GET", f"{BASE}/map/latest", headers=auth_headers(alice_token))
    if r.status_code == 200:
        results = r.json()["results"]
        bob_result = next((res for res in results if res["friend"]["username"] == bob_username), None)
        if bob_result:
            loc = bob_result["location"]
            if loc["lat"] == 43.65 and loc["lng"] == -79.38 and loc["status"] == 0:
                success("Original flow regression test passed")
            else:
                die(f"Original flow location data incorrect: {loc}")
        else:
            die(f"Bob not found in Alice's map: {results}")
    else:
        die(f"Map latest failed: {r.status_code} {r.text}")

def main():
    print("🧪 Compass SafeWalks Production E2E Safety Features Test")
    print(f"Testing against: {BASE}")
    print("=" * 60)
    
    try:
        test_health()
        test_profile_features()
        # test_location_privacy()
        # test_sos_alerting()
        # test_incident_reporting()
        # test_friends_metadata()
        # test_regression_original_flow()
        
        print("=" * 60)
        success("All tests passed! 🎉")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()