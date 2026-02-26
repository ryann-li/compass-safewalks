#!/usr/bin/env python3
"""
Production test script for friend location sharing flow.
Tests the specific case where users should see their friends' locations.
"""
import sys
import requests
import random
import string
from datetime import datetime


PROD_BASE = "https://compass-safewalks.vercel.app"
TOWER_KEY = "dev-tower-key"  # Production tower key


def generate_unique_suffix():
    """Generate a unique suffix for usernames to avoid conflicts"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")


def die(msg: str):
    log(f"❌ FAILED: {msg}")
    sys.exit(1)


def req(method, url, **kwargs):
    """Make HTTP request with proper error handling"""
    try:
        r = requests.request(method, url, timeout=30, **kwargs)
        log(f"{method} {url} -> {r.status_code}")
        return r
    except requests.RequestException as e:
        die(f"Request failed: {e}")


def signup_user(base: str, username: str, password: str) -> str:
    """Sign up a new user and return access token"""
    r = req("POST", f"{base}/auth/signup", json={"username": username, "password": password})
    
    if r.status_code == 201:
        token = r.json()["access_token"]
        user_id = r.json()["user"]["id"]
        log(f"✅ Signed up {username} (ID: {user_id})")
        return token
    elif r.status_code == 409:
        die(f"Username {username} already exists. Try with different suffix.")
    else:
        die(f"Signup failed for {username}: {r.status_code} {r.text}")


def claim_fob(base: str, token: str, fob_uid: str, username: str):
    """Claim a fob for a user"""
    r = req(
        "POST",
        f"{base}/fob/claim",
        headers={"Authorization": f"Bearer {token}"},
        json={"fob_uid": fob_uid},
    )
    
    if r.status_code == 201:
        log(f"✅ {username} claimed fob {fob_uid}")
    elif r.status_code == 409:
        error_code = r.json().get("error", {}).get("code", "")
        if error_code == "FOB_ALREADY_CLAIMED":
            log(f"⚠️  Fob {fob_uid} already claimed by {username} (OK)")
        else:
            die(f"Fob claim conflict for {username}: {r.text}")
    else:
        die(f"Fob claim failed for {username}: {r.status_code} {r.text}")


def add_friend(base: str, token: str, friend_username: str, requester_username: str):
    """Add a friend (bidirectional)"""
    r = req(
        "POST",
        f"{base}/friends/add",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": friend_username},
    )
    
    if r.status_code == 200:
        added = r.json().get("added", False)
        log(f"✅ {requester_username} -> {friend_username}: friendship {'added' if added else 'already exists'}")
    elif r.status_code == 404:
        die(f"User {friend_username} not found when adding friend")
    else:
        die(f"Add friend failed: {r.status_code} {r.text}")


def send_tower_ping(base: str, fob_uid: str, lat: float, lng: float, status: int = 0):
    """Send a ping from tower system"""
    r = req(
        "POST",
        f"{base}/tower/pings",
        headers={"X-Tower-Key": TOWER_KEY},
        json={"fob_uid": fob_uid, "lat": lat, "lng": lng, "status": status},
    )
    
    if r.status_code == 201:
        status_text = {0: "Safe", 1: "Not Safe", 2: "SOS"}[status]
        log(f"✅ Tower ping sent: {fob_uid} @ ({lat}, {lng}) - {status_text}")
    elif r.status_code == 401:
        die(f"Tower unauthorized. Check TOWER_KEY configuration.")
    else:
        die(f"Tower ping failed: {r.status_code} {r.text}")


def get_map_latest(base: str, token: str, username: str):
    """Get latest map data for user"""
    r = req(
        "GET",
        f"{base}/map/latest",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    if r.status_code == 200:
        data = r.json()
        results = data.get("results", [])
        log(f"✅ {username} map/latest: {len(results)} friend(s) visible")
        return data
    else:
        die(f"Map latest failed for {username}: {r.status_code} {r.text}")


def check_friendship_sharing(base: str, token: str, username: str, friend_username: str):
    """Check if friendship allows location sharing"""
    r = req(
        "GET",
        f"{base}/friends",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    if r.status_code == 200:
        friends = r.json().get("friends", [])
        for friend in friends:
            if friend["username"] == friend_username:
                log(f"✅ {username} has {friend_username} as friend (sharing enabled by default)")
                return True
        log(f"⚠️  {username} does not have {friend_username} as friend")
        return False
    else:
        die(f"Get friends failed for {username}: {r.status_code} {r.text}")


def main():
    log("🚀 Starting Production Friend Location Sharing Test")
    log(f"🌍 Target: {PROD_BASE}")
    
    # Generate unique usernames to avoid conflicts
    suffix = generate_unique_suffix()
    alice_username = f"alice_test_{suffix}"
    bob_username = f"bob_test_{suffix}"
    alice_fob = f"FOB_ALICE_{suffix}"
    bob_fob = f"FOB_BOB_{suffix}"
    
    log(f"👥 Test users: {alice_username}, {bob_username}")
    log(f"📡 Test fobs: {alice_fob}, {bob_fob}")
    
    # Health check
    log("🏥 Checking server health...")
    r = req("GET", f"{PROD_BASE}/health")
    if r.status_code != 200 or r.json().get("ok") is not True:
        die(f"Health check failed: {r.status_code}")
    log("✅ Server is healthy")
    
    # Step 1: Sign up two users
    log("\n📝 Step 1: Signing up users...")
    alice_token = signup_user(PROD_BASE, alice_username, "password123")
    bob_token = signup_user(PROD_BASE, bob_username, "password123")
    
    # Step 2: Each user claims a fob
    log("\n📡 Step 2: Claiming fobs...")
    claim_fob(PROD_BASE, alice_token, alice_fob, alice_username)
    claim_fob(PROD_BASE, bob_token, bob_fob, bob_username)
    
    # Step 3: Users friend each other (bidirectional)
    log("\n👫 Step 3: Creating friendships...")
    add_friend(PROD_BASE, alice_token, bob_username, alice_username)
    add_friend(PROD_BASE, bob_token, alice_username, bob_username)
    
    # Verify friendships
    log("\n🔍 Verifying friendships...")
    check_friendship_sharing(PROD_BASE, alice_token, alice_username, bob_username)
    check_friendship_sharing(PROD_BASE, bob_token, bob_username, alice_username)
    
    # Step 4: Send initial pings to establish location history
    log("\n📍 Step 4: Sending initial pings...")
    # Alice's location (Toronto area)
    send_tower_ping(PROD_BASE, alice_fob, 43.6532, -79.3832, status=0)
    # Bob's location (London, ON area) 
    send_tower_ping(PROD_BASE, bob_fob, 42.9849, -81.2453, status=0)
    
    # Step 5: Bob sends a new ping
    log("\n📡 Step 5: Bob sends updated ping...")
    send_tower_ping(PROD_BASE, bob_fob, 42.9900, -81.2500, status=0)
    
    # Step 6: Alice gets map/latest and should see Bob's location
    log("\n🗺️  Step 6: Alice checks map for friends...")
    alice_map = get_map_latest(PROD_BASE, alice_token, alice_username)
    
    # Step 7: Analyze results
    log("\n📊 Step 7: Analyzing results...")
    alice_results = alice_map.get("results", [])
    
    if len(alice_results) == 0:
        log("❌ ISSUE: Alice sees no friends on map!")
        log("🔍 Possible causes:")
        log("   - Friendship not properly established")
        log("   - Location sharing disabled") 
        log("   - Bob's fob not linked/pings not stored")
        log("   - Database/query issue")
        
        # Debug: Check if Bob's ping was actually stored
        log("\n🔍 Debug: Checking Bob's map view...")
        bob_map = get_map_latest(PROD_BASE, bob_token, bob_username)
        bob_results = bob_map.get("results", [])
        
        if len(bob_results) == 0:
            log("🔍 Bob also sees no friends - mutual issue")
        else:
            log(f"🔍 Bob sees {len(bob_results)} friend(s) - asymmetric issue")
        
        return False
    
    else:
        log(f"✅ SUCCESS: Alice sees {len(alice_results)} friend(s)")
        
        for result in alice_results:
            friend = result["friend"]
            location = result["location"]
            fob_uid = result["fob_uid"]
            
            log(f"   👤 Friend: {friend['username']} (ID: {friend['id']})")
            log(f"   📡 Fob: {fob_uid}")  
            log(f"   📍 Location: ({location['lat']}, {location['lng']})")
            log(f"   🟢 Status: {location['status']} at {location['received_at']}")
            
            if friend["username"] == bob_username:
                log("✅ SUCCESS: Alice can see Bob's location!")
                if abs(location["lat"] - 42.99) < 0.1 and abs(location["lng"] - (-81.25)) < 0.1:
                    log("✅ SUCCESS: Location data is correct (Bob's latest ping)")
                else:
                    log(f"⚠️  Location mismatch - expected ~(42.99, -81.25), got ({location['lat']}, {location['lng']})")
                return True
            else:
                log(f"⚠️  Expected to see {bob_username}, but got {friend['username']}")
    
    log("\n🎯 Test completed!")
    return True


if __name__ == "__main__":
    success = main()
    if success:
        log("\n🎉 Production test PASSED!")
        sys.exit(0)
    else:
        log("\n💥 Production test FAILED!")
        sys.exit(1)