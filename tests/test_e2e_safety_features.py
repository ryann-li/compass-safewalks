"""
Comprehensive E2E integration tests for Compass SafeWalks safety features.

Covers:
  1. Profile update flow (upload-url + PATCH /auth/me)
  2. Location privacy ("Invisibility" test via share-location toggle)
  3. SOS alerting (status=2 on tower pings + map/latest verification)
  4. Incident reporting (POST /incidents)
  5. Friends list metadata (display_name, profile_picture_url, latest_ping_received_at)
  6. Regression: all original flows still work
"""

TOWER_KEY = "test-tower-key"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def tower_headers() -> dict[str, str]:
    return {"X-Tower-Key": TOWER_KEY}


def signup(client, username: str, password: str = "pw") -> dict:
    r = client.post("/auth/signup", json={"username": username, "password": password})
    assert r.status_code == 201, f"Signup {username}: {r.text}"
    data = r.json()
    assert "access_token" in data
    assert data["user"]["username"] == username
    return data


def claim_fob(client, token: str, fob_uid: str):
    r = client.post("/fob/claim", json={"fob_uid": fob_uid}, headers=auth_headers(token))
    assert r.status_code == 201, f"Claim fob {fob_uid}: {r.text}"


def add_friend(client, token: str, friend_username: str):
    r = client.post("/friends/add", json={"username": friend_username}, headers=auth_headers(token))
    assert r.status_code == 200, f"Add friend {friend_username}: {r.text}"


def tower_ping(client, fob_uid: str, lat: float, lng: float, status: int = 0):
    r = client.post(
        "/tower/pings",
        json={"fob_uid": fob_uid, "lat": lat, "lng": lng, "status": status},
        headers=tower_headers(),
    )
    assert r.status_code == 201, f"Tower ping {fob_uid}: {r.text}"


# ===========================================================================
# 1. PROFILE UPDATE FLOW
# ===========================================================================

def test_profile_upload_url_and_update(client, monkeypatch):
    """GET /auth/storage/upload-url returns signed URLs; PATCH /auth/me saves profile data."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "fake-blob-token-for-test")

    alice = signup(client, "alice_profile")
    token = alice["access_token"]

    # --- GET /auth/storage/upload-url ---
    r = client.get(
        "/auth/storage/upload-url",
        params={"filename": "avatar.png"},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "upload_url" in body
    assert "blob_url" in body
    # The fallback HMAC path should produce a blob.vercel-storage.com URL
    assert "blob.vercel-storage.com" in body["upload_url"]

    # --- PATCH /auth/me with valid blob URL ---
    mock_pic_url = "https://public.blob.vercel-storage.com/avatars/test/avatar.png"
    r = client.patch(
        "/auth/me",
        json={"display_name": "Alice Wonderland", "profile_picture_url": mock_pic_url},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    profile = r.json()
    assert profile["display_name"] == "Alice Wonderland"
    assert profile["profile_picture_url"] == mock_pic_url
    assert profile["username"] == "alice_profile"

    # --- Verify persistence by updating only display_name ---
    r = client.patch(
        "/auth/me",
        json={"display_name": "Alice W."},
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    profile2 = r.json()
    assert profile2["display_name"] == "Alice W."
    # picture URL should still be there (not nulled out)
    assert profile2["profile_picture_url"] == mock_pic_url


def test_profile_update_rejects_bad_url(client, monkeypatch):
    """PATCH /auth/me must reject profile_picture_url from non-Vercel domains."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_badurl")
    token = alice["access_token"]

    r = client.patch(
        "/auth/me",
        json={"profile_picture_url": "https://evil.example.com/avatar.png"},
        headers=auth_headers(token),
    )
    assert r.status_code == 400, r.text
    assert "INVALID_URL" in r.text


def test_upload_url_requires_blob_token(client, monkeypatch):
    """GET /auth/storage/upload-url returns 503 when BLOB_READ_WRITE_TOKEN is missing."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)
    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)

    alice = signup(client, "alice_notoken")
    token = alice["access_token"]

    r = client.get(
        "/auth/storage/upload-url",
        params={"filename": "avatar.png"},
        headers=auth_headers(token),
    )
    assert r.status_code == 503, r.text
    assert "STORAGE_UNAVAILABLE" in r.text


# ===========================================================================
# 2. LOCATION PRIVACY — THE "INVISIBILITY" TEST
# ===========================================================================

def test_location_privacy_share_toggle(client, monkeypatch):
    """
    When Alice disables location sharing for Bob, Bob's map/latest
    must no longer include Alice.
    """
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_priv")
    bob = signup(client, "bob_priv")
    alice_token = alice["access_token"]
    bob_token = bob["access_token"]

    # Setup fobs & friendship
    claim_fob(client, alice_token, "FOB_ALICE_PRIV")
    claim_fob(client, bob_token, "FOB_BOB_PRIV")
    add_friend(client, alice_token, "bob_priv")

    # Tower pings for Alice's fob
    tower_ping(client, "FOB_ALICE_PRIV", 43.65, -79.38)

    # --- BASELINE: Bob should see Alice on the map ---
    r = client.get("/map/latest", headers=auth_headers(bob_token))
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    alice_results = [res for res in results if res["friend"]["username"] == "alice_priv"]
    assert len(alice_results) == 1, f"Expected Alice in map results, got: {results}"

    # --- ACTION: Alice disables sharing for Bob ---
    r = client.patch(
        "/friends/share-location",
        json={"username": "bob_priv", "enabled": False},
        headers=auth_headers(alice_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["updated"] is True
    assert body["is_sharing_location"] is False

    # --- VERIFY: Bob's map/latest must NOT include Alice anymore ---
    r = client.get("/map/latest", headers=auth_headers(bob_token))
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    alice_results = [res for res in results if res["friend"]["username"] == "alice_priv"]
    assert len(alice_results) == 0, f"Alice should be invisible, got: {results}"

    # --- RE-ENABLE: Alice turns sharing back on ---
    r = client.patch(
        "/friends/share-location",
        json={"username": "bob_priv", "enabled": True},
        headers=auth_headers(alice_token),
    )
    assert r.status_code == 200
    assert r.json()["is_sharing_location"] is True

    # --- VERIFY: Bob sees Alice again ---
    r = client.get("/map/latest", headers=auth_headers(bob_token))
    assert r.status_code == 200
    results = r.json()["results"]
    alice_results = [res for res in results if res["friend"]["username"] == "alice_priv"]
    assert len(alice_results) == 1


# ===========================================================================
# 3. SOS ALERTING
# ===========================================================================

def test_sos_ping_status_and_map(client, monkeypatch):
    """
    A tower ping with status=2 (SOS) should:
      - Be stored and returned as status=2 in map/latest
      - Log a warning with 🚨 SOS ALERT
    """
    from unittest.mock import patch

    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_sos")
    bob = signup(client, "bob_sos")
    alice_token = alice["access_token"]
    bob_token = bob["access_token"]

    claim_fob(client, alice_token, "FOB_ALICE_SOS")
    add_friend(client, bob_token, "alice_sos")

    # Send an initial safe ping
    tower_ping(client, "FOB_ALICE_SOS", 43.65, -79.38, status=0)

    # Verify safe status
    r = client.get("/map/latest", headers=auth_headers(bob_token))
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 1
    assert results[0]["location"]["status"] == 0

    # --- SOS ping — patch the logger to capture the warning ---
    with patch("app.routes.tower_ingest.logger") as mock_logger:
        tower_ping(client, "FOB_ALICE_SOS", 43.66, -79.39, status=2)

        # Verify SOS warning was logged
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        fmt_string = call_args[0][0]
        assert "SOS ALERT" in fmt_string

    # --- Verify map/latest now shows status=2 (the latest ping) ---
    r = client.get("/map/latest", headers=auth_headers(bob_token))
    assert r.status_code == 200
    results = r.json()["results"]
    alice_result = [res for res in results if res["friend"]["username"] == "alice_sos"]
    assert len(alice_result) == 1
    assert alice_result[0]["location"]["status"] == 2
    assert alice_result[0]["location"]["lat"] == 43.66
    assert alice_result[0]["location"]["lng"] == -79.39


def test_tower_ping_default_status_is_zero(client, monkeypatch):
    """Tower ping without explicit status should default to 0 (Safe)."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_def")
    bob = signup(client, "bob_def")
    alice_token = alice["access_token"]
    bob_token = bob["access_token"]

    claim_fob(client, alice_token, "FOB_ALICE_DEF")
    add_friend(client, bob_token, "alice_def")

    # Ping without status field
    r = client.post(
        "/tower/pings",
        json={"fob_uid": "FOB_ALICE_DEF", "lat": 43.65, "lng": -79.38},
        headers=tower_headers(),
    )
    assert r.status_code == 201

    r = client.get("/map/latest", headers=auth_headers(bob_token))
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 1
    assert results[0]["location"]["status"] == 0


# ===========================================================================
# 4. INCIDENT REPORTING
# ===========================================================================

def test_create_incident(client, monkeypatch):
    """POST /incidents creates and returns the incident record."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_inc")
    token = alice["access_token"]

    r = client.post(
        "/incidents",
        json={
            "lat": 43.6532,
            "lng": -79.3832,
            "description": "Suspicious activity near the park entrance",
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["lat"] == 43.6532
    assert body["lng"] == -79.3832
    assert body["description"] == "Suspicious activity near the park entrance"
    assert "id" in body
    assert "reporter_id" in body
    assert "created_at" in body
    # reporter_id should match Alice's user id
    assert body["reporter_id"] == alice["user"]["id"]


def test_incident_requires_auth(client, monkeypatch):
    """POST /incidents without a token should return 401."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    r = client.post(
        "/incidents",
        json={"lat": 43.65, "lng": -79.38, "description": "test"},
    )
    assert r.status_code == 401


# ===========================================================================
# 5. FRIENDS LIST METADATA
# ===========================================================================

def test_friends_list_includes_metadata(client, monkeypatch):
    """
    GET /friends returns display_name, profile_picture_url, and
    latest_ping_received_at for each friend.
    """
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_meta")
    bob = signup(client, "bob_meta")
    alice_token = alice["access_token"]
    bob_token = bob["access_token"]

    # Set Bob's profile
    mock_pic = "https://public.blob.vercel-storage.com/avatars/bob/pic.png"
    r = client.patch(
        "/auth/me",
        json={"display_name": "Bob Builder", "profile_picture_url": mock_pic},
        headers=auth_headers(bob_token),
    )
    assert r.status_code == 200

    # Claim a fob for Bob and send a ping
    claim_fob(client, bob_token, "FOB_BOB_META")
    tower_ping(client, "FOB_BOB_META", 43.47, -80.54)

    # Alice adds Bob
    add_friend(client, alice_token, "bob_meta")

    # --- GET /friends for Alice ---
    r = client.get("/friends", headers=auth_headers(alice_token))
    assert r.status_code == 200, r.text
    friends = r.json()["friends"]
    assert len(friends) == 1

    bob_friend = friends[0]
    assert bob_friend["username"] == "bob_meta"
    assert bob_friend["display_name"] == "Bob Builder"
    assert bob_friend["profile_picture_url"] == mock_pic
    assert bob_friend["latest_ping_received_at"] is not None


def test_friends_list_null_metadata_when_unset(client, monkeypatch):
    """Friends with no profile or pings should return nulls gracefully."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_null")
    bob = signup(client, "bob_null")
    alice_token = alice["access_token"]

    add_friend(client, alice_token, "bob_null")

    r = client.get("/friends", headers=auth_headers(alice_token))
    assert r.status_code == 200
    friends = r.json()["friends"]
    assert len(friends) == 1

    bob_friend = friends[0]
    assert bob_friend["display_name"] is None
    assert bob_friend["profile_picture_url"] is None
    assert bob_friend["latest_ping_received_at"] is None


# ===========================================================================
# 6. REGRESSION: ORIGINAL HAPPY-PATH E2E
# ===========================================================================

def test_original_happy_path_e2e(client, monkeypatch):
    """The original end-to-end flow still works with the new schema."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    # signup
    alice = signup(client, "alice_reg")
    bob = signup(client, "bob_reg")
    alice_token = alice["access_token"]
    bob_token = bob["access_token"]

    # claim fobs
    claim_fob(client, alice_token, "FOB_ALICE_REG")
    claim_fob(client, bob_token, "FOB_BOB_REG")

    # alice adds bob
    add_friend(client, alice_token, "bob_reg")

    # tower pings bob's fob
    tower_ping(client, "FOB_BOB_REG", 43.65, -79.38)

    # alice sees bob on map
    r = client.get("/map/latest", headers=auth_headers(alice_token))
    assert r.status_code == 200
    body = r.json()
    assert body["window_minutes"] is None
    results = body["results"]
    assert len(results) == 1
    res = results[0]
    assert res["friend"]["username"] == "bob_reg"
    assert res["fob_uid"] == "FOB_BOB_REG"
    assert res["location"]["lat"] == 43.65
    assert res["location"]["lng"] == -79.38
    assert res["location"]["status"] == 0  # default safe
    assert "received_at" in res["location"]


def test_mutual_friends_still_works(client, monkeypatch):
    """Adding a friend is still mutual."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_mut")
    bob = signup(client, "bob_mut")
    alice_token = alice["access_token"]
    bob_token = bob["access_token"]

    add_friend(client, alice_token, "bob_mut")

    r = client.get("/friends", headers=auth_headers(bob_token))
    assert r.status_code == 200
    friends = r.json()["friends"]
    assert any(f["username"] == "alice_mut" for f in friends)


def test_tower_auth_still_enforced(client, monkeypatch):
    """Tower key enforcement hasn't regressed."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    body = {"fob_uid": "FOB_X", "lat": 43.65, "lng": -79.38}

    # missing key
    r = client.post("/tower/pings", json=body)
    assert r.status_code == 401

    # wrong key
    r = client.post("/tower/pings", json=body, headers={"X-Tower-Key": "wrong"})
    assert r.status_code == 401

    # correct key
    r = client.post("/tower/pings", json=body, headers=tower_headers())
    assert r.status_code == 201


def test_fob_uniqueness_still_enforced(client, monkeypatch):
    """Two users can't claim the same fob."""
    monkeypatch.setenv("TOWER_SHARED_KEY", TOWER_KEY)

    alice = signup(client, "alice_fob")
    bob = signup(client, "bob_fob")
    alice_token = alice["access_token"]
    bob_token = bob["access_token"]

    claim_fob(client, alice_token, "FOB_UNIQUE")

    r = client.post("/fob/claim", json={"fob_uid": "FOB_UNIQUE"}, headers=auth_headers(bob_token))
    assert r.status_code == 409


def test_health_endpoint(client):
    """Health check still works."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
