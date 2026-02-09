import sys
import requests


BASE = "https://compass-safewalks.vercel.app"
TOWER_KEY = "dev-tower-key"

LOCAL_BASE = "http://localhost:8000"

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
        return r.json()["access_token"]
    if r.status_code == 409:
        r2 = req("POST", f"{base}/auth/login", json={"username": username, "password": password})
        if r2.status_code != 200:
            die(f"Login failed for {username}: {r2.status_code} {r2.text}")
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

def tower_ping(base: str, tower_key: str, tower_id: str, fob_uid: str, rssi: int = -67):
    r = req(
        "POST",
        f"{base}/tower/pings",
        headers={"X-Tower-Key": tower_key},
        json={"tower_id": tower_id, "fob_uid": fob_uid, "rssi": rssi},
    )
    if r.status_code == 201:
        print(f"Tower ping stored for {fob_uid} @ {tower_id}")
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

    # Users
    alice_token = get_token(BASE, "alice", "pw")
    print("Got alice token")
    bob_token = get_token(BASE, "bob", "pw")
    print("Got bob token")

    # Fobs
    claim_fob(BASE, alice_token, "FOB_ALICE")
    claim_fob(BASE, bob_token, "FOB_BOB")

    # Friends
    add_friend(BASE, alice_token, "bob")

    # Tower ping for bob
    tower_ping(BASE, TOWER_KEY, "tower-1", "FOB_BOB", -67)

    # Map latest
    data = map_latest(BASE, alice_token)
    results = data.get("results", [])
    if not results:
        die(f"Expected at least 1 result, got: {data}")

    print(f"Latest map data: {results}")

if __name__ == "__main__":
    main()
