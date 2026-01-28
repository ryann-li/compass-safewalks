from datetime import datetime, timedelta, timezone


TOWER_KEY = "test-tower-key"


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_happy_path_end_to_end(client, monkeypatch):
    # Configure tower shared key
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    # signup alice, bob
    alice_signup = client.post("/auth/signup", json={"username": "alice", "password": "pw"})
    assert alice_signup.status_code == 201, alice_signup.text
    alice_token = alice_signup.json()["access_token"]

    bob_signup = client.post("/auth/signup", json={"username": "bob", "password": "pw"})
    assert bob_signup.status_code == 201
    bob_token = bob_signup.json()["access_token"]

    # claim fobs
    FOB_ALICE = "FOB_ALICE"
    FOB_BOB = "FOB_BOB"

    r = client.post("/fob/claim", json={"fob_uid": FOB_ALICE}, headers=auth_headers(alice_token))
    assert r.status_code == 201

    r = client.post("/fob/claim", json={"fob_uid": FOB_BOB}, headers=auth_headers(bob_token))
    assert r.status_code == 201

    # alice adds bob
    r = client.post("/friends/add", json={"username": "bob"}, headers=auth_headers(alice_token))
    assert r.status_code == 200

    # tower posts ping for FOB_BOB
    now = datetime.now(timezone.utc) - timedelta(minutes=1)
    ping_body = {
        "tower_id": "tower-1",
        "fob_uid": FOB_BOB,
        "tower_reported_at": now.isoformat(),
        "rssi": -67,
    }
    r = client.post("/tower/pings", json=ping_body, headers={"X-Tower-Key": TOWER_KEY})
    assert r.status_code == 201, r.text

    # alice gets map/latest
    r = client.get("/map/latest", headers=auth_headers(alice_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["window_minutes"] is None
    results = body["results"]
    assert len(results) == 1
    res = results[0]
    assert res["friend"]["username"] == "bob"
    assert res["fob_uid"] == FOB_BOB
    assert res["ping"]["tower"]["id"] == "tower-1"
    assert "lat" in res["ping"]["tower"]
    assert "lng" in res["ping"]["tower"]


def test_mutual_friends_invariant(client, monkeypatch):
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = client.post("/auth/signup", json={"username": "alice2", "password": "pw"}).json()
    alice_token = alice["access_token"]
    bob = client.post("/auth/signup", json={"username": "bob2", "password": "pw"}).json()
    bob_token = bob["access_token"]

    r = client.post("/friends/add", json={"username": "bob2"}, headers=auth_headers(alice_token))
    assert r.status_code == 200

    r = client.get("/friends", headers=auth_headers(bob_token))
    assert r.status_code == 200
    friends = r.json()["friends"]
    assert any(f["username"] == "alice2" for f in friends)


def test_tower_auth_enforcement(client, monkeypatch):
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    body = {"tower_id": "tower-1", "fob_uid": "FOB_X"}

    # missing key
    r = client.post("/tower/pings", json=body)
    assert r.status_code == 401

    # wrong key
    r = client.post("/tower/pings", json=body, headers={"X-Tower-Key": "wrong"})
    assert r.status_code == 401

    # correct key but invalid tower
    body["tower_id"] = "invalid-tower"
    r = client.post("/tower/pings", json=body, headers={"X-Tower-Key": TOWER_KEY})
    assert r.status_code == 404


def test_fob_uniqueness(client, monkeypatch):
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = client.post("/auth/signup", json={"username": "alice3", "password": "pw"})
    assert alice.status_code == 201
    alice_token = alice.json()["access_token"]

    bob = client.post("/auth/signup", json={"username": "bob3", "password": "pw"})
    assert bob.status_code == 201
    bob_token = bob.json()["access_token"]

    FOB_X = "FOB_X"

    r = client.post("/fob/claim", json={"fob_uid": FOB_X}, headers=auth_headers(alice_token))
    assert r.status_code == 201

    r = client.post("/fob/claim", json={"fob_uid": FOB_X}, headers=auth_headers(bob_token))
    assert r.status_code == 409

