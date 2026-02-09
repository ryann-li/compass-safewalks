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

def tower_ping(base: str, fob_uid: str, lat: float, lng: float):
    r = req(
        "POST",
        f"{base}/tower/pings",
        headers={"X-Tower-Key": TOWER_KEY},
        json={"fob_uid": fob_uid, "lat": lat, "lng": lng},
    )
    if r.status_code == 201:
        print(f"Tower ping stored for {fob_uid} @ {lat},{lng}")
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
    
    # alice gets map/latest
    body = map_latest(BASE, alice_token)
    print("Map latest response:")
    print(body)


if __name__ == "__main__":
    main()
