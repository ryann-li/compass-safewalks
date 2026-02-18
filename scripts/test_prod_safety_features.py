import requests
import time

BASE_URL = "https://compass-safewalks.vercel.app"
TOWER_KEY = "dev-tower-key"

def run_test():
    print("🧪 Compass SafeWalks Full Flow Test")
    print("=" * 50)
    
    # 1. Setup - Create Alice and Bob
    timestamp = int(time.time())
    alice_username = f"alice_test_{timestamp}"
    bob_username = f"bob_test_{timestamp}"
    
    print("1. Creating users...")
    alice_data = {"username": alice_username, "password": "password123"}
    bob_data = {"username": bob_username, "password": "password123"}
    
    # Signup Alice
    alice_signup = requests.post(f"{BASE_URL}/auth/signup", json=alice_data)
    print(f"  Alice signup: {alice_signup.status_code}")
    alice_login = requests.post(f"{BASE_URL}/auth/login", json=alice_data).json()
    alice_token = alice_login["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    
    # Signup Bob  
    bob_signup = requests.post(f"{BASE_URL}/auth/signup", json=bob_data)
    print(f"  Bob signup: {bob_signup.status_code}")
    bob_login = requests.post(f"{BASE_URL}/auth/login", json=bob_data).json()
    bob_token = bob_login["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # 2. Update Profiles
    print("\n2. Updating profiles...")
    
    # Alice profile with avatar
    try:
        with open("/Users/ryanli/Desktop/peter.png", "rb") as f:
            files = {
                "display_name": (None, "Alice in Wonderland"),
                "profile_picture": ("peter.png", f, "image/png")
            }
            alice_profile = requests.patch(f"{BASE_URL}/auth/me", headers=alice_headers, files=files)
            print(f"  Alice profile updated: {alice_profile.status_code}")
            if alice_profile.status_code == 200:
                profile = alice_profile.json()
                print(f"    Avatar URL: {profile.get('profile_picture_url', 'None')}")
    except FileNotFoundError:
        # Fallback without file
        files = {"display_name": (None, "Alice in Wonderland")}
        alice_profile = requests.patch(f"{BASE_URL}/auth/me", headers=alice_headers, files=files)
        print(f"  Alice profile updated (no avatar): {alice_profile.status_code}")
    
    # Bob profile (name only)
    files = {"display_name": (None, "Bob the Builder")}
    bob_profile = requests.patch(f"{BASE_URL}/auth/me", headers=bob_headers, files=files)
    print(f"  Bob profile updated: {bob_profile.status_code}")

    # 3. Fob Claims
    print("\n3. Claiming fobs...")
    alice_fob = f"FOB_ALICE_{timestamp}"
    bob_fob = f"FOB_BOB_{timestamp}"
    
    alice_claim = requests.post(f"{BASE_URL}/fob/claim", headers=alice_headers, json={"fob_uid": alice_fob})
    bob_claim = requests.post(f"{BASE_URL}/fob/claim", headers=bob_headers, json={"fob_uid": bob_fob})
    print(f"  Alice fob claim: {alice_claim.status_code}")
    print(f"  Bob fob claim: {bob_claim.status_code}")

    # 4. Add Friendship
    print("\n4. Adding friendship...")
    friendship = requests.post(f"{BASE_URL}/friends/add", headers=alice_headers, json={"username": bob_username})
    print(f"  Alice adds Bob: {friendship.status_code}")
    
    # Check friends list
    friends_list = requests.get(f"{BASE_URL}/friends", headers=alice_headers).json()
    print(f"  Alice's friends: {len(friends_list['friends'])}")

    # 5. Send Pings
    print("\n5. Sending location pings...")
    
    # Alice ping (Safe)
    alice_ping = {"fob_uid": alice_fob, "lat": 43.6532, "lng": -79.3832, "status": 0}
    ping1 = requests.post(f"{BASE_URL}/tower/pings", headers={"X-Tower-Key": TOWER_KEY}, json=alice_ping)
    print(f"  Alice ping (Safe): {ping1.status_code}")
    
    # Bob ping (Safe)
    bob_ping = {"fob_uid": bob_fob, "lat": 43.6612, "lng": -79.3944, "status": 0}
    ping2 = requests.post(f"{BASE_URL}/tower/pings", headers={"X-Tower-Key": TOWER_KEY}, json=bob_ping)
    print(f"  Bob ping (Safe): {ping2.status_code}")

    # 6. Check Map (Alice's view)
    print("\n6. Checking map visibility...")
    map_res = requests.get(f"{BASE_URL}/map/latest", headers=alice_headers).json()
    print(f"  Alice sees {len(map_res['results'])} locations on map")
    for result in map_res['results']:
        friend = result['friend']['username']
        loc = result['location']
        print(f"    {friend}: ({loc['lat']}, {loc['lng']}) status={loc['status']}")

    # 7. Test Privacy Controls
    print("\n7. Testing privacy controls...")
    
    # Bob disables sharing with Alice
    privacy_off = requests.patch(f"{BASE_URL}/friends/share-location", 
                                headers=bob_headers, 
                                json={"username": alice_username, "enabled": False})
    print(f"  Bob disables sharing: {privacy_off.status_code}")
    
    # Alice checks map again
    map_res = requests.get(f"{BASE_URL}/map/latest", headers=alice_headers).json()
    print(f"  Alice now sees {len(map_res['results'])} locations (should be 0)")
    
    # Bob re-enables sharing
    privacy_on = requests.patch(f"{BASE_URL}/friends/share-location",
                               headers=bob_headers,
                               json={"username": alice_username, "enabled": True})
    print(f"  Bob re-enables sharing: {privacy_on.status_code}")
    
    # Alice checks map again
    map_res = requests.get(f"{BASE_URL}/map/latest", headers=alice_headers).json()
    print(f"  Alice now sees {len(map_res['results'])} locations (should be 1)")

    # 8. Test SOS Alert
    print("\n8. Testing SOS alert...")
    sos_ping = {"fob_uid": bob_fob, "lat": 43.6650, "lng": -79.3900, "status": 2}
    sos_response = requests.post(f"{BASE_URL}/tower/pings", headers={"X-Tower-Key": TOWER_KEY}, json=sos_ping)
    print(f"  Bob SOS ping: {sos_response.status_code}")
    
    # Check map shows SOS status
    map_res = requests.get(f"{BASE_URL}/map/latest", headers=alice_headers).json()
    if map_res['results']:
        sos_status = map_res['results'][0]['location']['status']
        print(f"  Map shows status: {sos_status} (2=SOS)")

    # 9. Incident Reporting
    print("\n9. Testing incident reporting...")
    incident = {
        "lat": 43.6532, 
        "lng": -79.3832, 
        "description": f"Test incident report at {timestamp}"
    }
    incident_res = requests.post(f"{BASE_URL}/incidents", headers=alice_headers, json=incident)
    print(f"  Incident report: {incident_res.status_code}")
    if incident_res.status_code == 201:
        incident_data = incident_res.json()
        print(f"    Incident ID: {incident_data['id']}")

    # 10. Profile Retrieval
    print("\n10. Final profile check...")
    alice_final = requests.get(f"{BASE_URL}/auth/me", headers=alice_headers).json()
    bob_final = requests.get(f"{BASE_URL}/auth/me", headers=bob_headers).json()
    print(f"  Alice: {alice_final['display_name']} (avatar: {bool(alice_final.get('profile_picture_url'))})")
    print(f"  Bob: {bob_final['display_name']} (avatar: {bool(bob_final.get('profile_picture_url'))})")

    print("\n" + "=" * 50)
    print("✅ Full flow test completed!")

if __name__ == "__main__":
    run_test()