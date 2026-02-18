# Compass SafeWalks API

**Base URL:** `https://compass-safewalks.vercel.app`

## Authentication

| Scheme | Header | Used by |
|--------|--------|---------|
| JWT Bearer | `Authorization: Bearer <JWT>` | Mobile clients |
| Tower Shared Key | `X-Tower-Key: <key>` | Tower hardware |

---

## Endpoints

### Health

`GET /health` → `{ "ok": true }`

`GET /` → `{ "ok": true }`

---

### Auth

| Method | Endpoint | Content-Type | Body / Params | Success | Errors |
|--------|----------|--------------|---------------|---------|--------|
| POST | `/auth/signup` | `application/json` | `{ "username", "password" }` | 201: `{ access_token, token_type, user: { id, username } }` | 409 `USERNAME_TAKEN` |
| POST | `/auth/login` | `application/json` | `{ "username", "password" }` | 200: `{ access_token, token_type, user: { id, username } }` | 401 `INVALID_CREDENTIALS` |
| GET | `/auth/me` | — | — | 200: `{ id, username, display_name, profile_picture_url }` | 401 `UNAUTHORIZED` |
| PATCH | `/auth/me` | `multipart/form-data` | `display_name` (form field, optional), `profile_picture` (file, optional) | 200: `{ id, username, display_name, profile_picture_url }` | 400 / 502 / 503 |

> **`GET /auth/me`** returns the authenticated user's profile.
>
> **`PATCH /auth/me`** accepts `multipart/form-data` with two optional parts:
> - `display_name` — plain text form field.
> - `profile_picture` — image file upload (`image/jpeg`, `image/png`, or `image/webp`; max 5 MB).
>
> If a file is provided the server proxies it to **Vercel Blob** (via `httpx`) using `BLOB_READ_WRITE_TOKEN`, stores the returned URL in `profile_picture_url`, and returns the updated profile.

---

### Fob *(JWT required)*

| Method | Endpoint | Body | Success | Errors |
|--------|----------|------|---------|--------|
| POST | `/fob/claim` | `{ "fob_uid" }` | 201: `{ fob_uid }` | 409 `FOB_ALREADY_CLAIMED` / `FOB_CONFLICT` |
| GET | `/fob/me` | — | 200: `{ fob_uid }` | 404 `FOB_NOT_FOUND` |

---

### Friends *(JWT required)*

| Method | Endpoint | Body | Success | Errors |
|--------|----------|------|---------|--------|
| POST | `/friends/add` | `{ "username" }` | 200: `{ added, friend: { id, username, display_name, profile_picture_url } }` | 400 `CANNOT_FRIEND_SELF` / 404 `USER_NOT_FOUND` |
| POST | `/friends/remove` | `{ "username" }` | 200: `{ removed }` | 404 `USER_NOT_FOUND` |
| GET | `/friends` | — | 200: `{ friends: [{ id, username, display_name, profile_picture_url, latest_ping_received_at }] }` | — |
| PATCH | `/friends/share-location` | `{ "username", "enabled" }` | 200: `{ updated, username, is_sharing_location }` | 404 `USER_NOT_FOUND` / `FRIENDSHIP_NOT_FOUND` |

> **`PATCH /friends/share-location`** toggles whether **you** share your location with a specific friend.
> The flag lives on the friendship row where `user_id = you`.

---

### Tower Ingestion *(Tower key required)*

| Method | Endpoint | Body | Success | Errors |
|--------|----------|------|---------|--------|
| POST | `/tower/pings` | `{ fob_uid, lat, lng, status? }` | 201: `{ stored }` | 401 `TOWER_UNAUTHORIZED` |

> Fobs are auto-registered on first tower ping if they don't already exist.
>
> `status` values: `0` = Safe (default), `1` = Not Safe, `2` = SOS.
>
> When `status == 2`, the server logs 🚨 **SOS ALERT** with user ID and coordinates.

---

### Map *(JWT required)*

| Method | Endpoint | Params | Success |
|--------|----------|--------|---------|
| GET | `/map/latest` | `window_minutes` (optional, int) | 200: `{ window_minutes, results: [{ friend: { id, username }, fob_uid, location: { lat, lng, status, received_at } }] }` |

> Only returns data for friends whose **reverse** friendship row has `is_sharing_location = true` (i.e. the friend has opted to share with you).
>
> `location.status` reflects the latest ping status (`0` = Safe, `1` = Not Safe, `2` = SOS).
>
> If `window_minutes` is omitted or `0`, all pings are returned (no time cutoff).

---

### Incidents *(JWT required)*

| Method | Endpoint | Body | Success |
|--------|----------|------|---------|
| POST | `/incidents` | `{ "lat", "lng", "description" }` | 201: `{ id, reporter_id, lat, lng, description, created_at }` |

> Report a community safety incident at a given location.

---

## Error Shape

All error responses follow:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

---

## Client Flow

1. `POST /auth/signup` or `/auth/login` → JWT
2. `GET /auth/me` to fetch current profile
3. `PATCH /auth/me` with `multipart/form-data` to update display name and/or upload avatar
4. `POST /fob/claim` (once, to bind hardware fob)
5. `POST /friends/add` to connect with other users
6. (Optional) `PATCH /friends/share-location` to control who sees your location
7. Towers → `POST /tower/pings` (with optional `status`)
8. Mobile → `GET /map/latest` to see friends' locations
9. (Optional) `POST /incidents` to report safety threats

---

## Schema

### Users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, auto-generated |
| username | Text | Unique, not null |
| password_hash | Text | Argon2, not null |
| display_name | Text | Nullable |
| profile_picture_url | Text | Nullable |
| created_at | Timestamptz | Default `now()` |

### Friendships
| Column | Type | Notes |
|--------|------|-------|
| user_id | UUID | PK, FK → users |
| friend_id | UUID | PK, FK → users |
| is_sharing_location | Boolean | Default `true` |
| created_at | Timestamptz | Default `now()` |

### Fobs
| Column | Type | Notes |
|--------|------|-------|
| fob_uid | Text | PK |
| owner_user_id | UUID | FK → users, nullable, unique |
| created_at | Timestamptz | Default `now()` |

### Pings
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | PK, auto-increment |
| fob_uid | Text | FK → fobs |
| lat | Float | |
| lng | Float | |
| status | Integer | `0`=Safe, `1`=Not Safe, `2`=SOS. Default `0` |
| received_at | Timestamptz | Default `now()` |

### Incidents
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, auto-generated |
| reporter_id | UUID | FK → users |
| lat | Float | |
| lng | Float | |
| description | Text | Not null |
| created_at | Timestamptz | Default `now()` |
