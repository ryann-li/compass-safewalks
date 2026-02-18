# Compass SafeWalks API

**Base URL:** `https://compass-safewalks.vercel.app`

## Auth

- Mobile: `Authorization: Bearer <JWT>`
- Tower: `X-Tower-Key: <key>`

---

## Endpoints

### Health
`GET /health` → `{ "ok": true }`

### Auth
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/auth/signup` | `{ "username", "password" }` | 201: `{ access_token, user }` / 409 |
| POST | `/auth/login` | `{ "username", "password" }` | 200: `{ access_token, user }` / 401 |
| GET | `/auth/storage/upload-url?filename=avatar.jpg` | — | 200: `{ upload_url, blob_url }` / 503 |
| PATCH | `/auth/me` | `{ "display_name?", "profile_picture_url?" }` | 200: `{ id, username, display_name, profile_picture_url }` / 400 |

> **`GET /auth/storage/upload-url`** generates a signed Vercel Blob upload URL scoped to the authenticated user.
> **`PATCH /auth/me`** validates that `profile_picture_url` belongs to the Vercel Blob storage domain.

### Fob *(JWT required)*
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/fob` | `{ "fob_uid, creator" }` | 201: `{ fob_uid }` / 409 |
| POST | `/fob/claim` | `{ "fob_uid" }` | 201: `{ fob_uid }` / 409 |
| GET | `/fob/me` | - | 200: `{ fob_uid }` / 404 |

### Friends *(JWT required)*
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/friends/add` | `{ "username" }` | 200: `{ added, friend }` |
| POST | `/friends/remove` | `{ "username" }` | 200: `{ removed }` |
| GET | `/friends` | - | 200: `{ friends: [{ id, username, display_name, profile_picture_url, latest_ping_received_at }] }` |
| PATCH | `/friends/share-location` | `{ "username", "enabled" }` | 200: `{ updated, username, is_sharing_location }` |

> **`PATCH /friends/share-location`** toggles whether you share your location with a specific friend.


### Tower Ingestion *(Tower key required)*
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/tower/pings` | `{ fob_uid, lat, lng, status? }` | 201: `{ stored }` / 401 TOWER_UNAUTHORIZED |

> Fobs are auto-registered on first tower ping if they don't already exist.
> `status` values: `0` = Safe (default), `1` = Not Safe, `2` = SOS.
> When `status == 2`, the server logs 🚨 **SOS ALERT** with user ID and coordinates.


### Map *(JWT required)*
| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/map/latest?window_minutes=10` | 200: `{ window_minutes, results: [{ friend, fob_uid, location: { lat, lng, status, received_at } }] }` |

> Only returns data for friends where `is_sharing_location` is **true**.
> `location.status` reflects the latest ping status (0=Safe, 1=Not Safe, 2=SOS).

### Incidents *(JWT required)*
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/incidents` | `{ "lat", "lng", "description" }` | 201: `{ id, reporter_id, lat, lng, description, created_at }` |

> Report a community safety incident at a given location.

---

## Client Flow

1. `POST /auth/signup` or `/auth/login` → JWT
2. (Optional) `GET /auth/storage/upload-url` → upload avatar → `PATCH /auth/me`
3. `POST /fob/claim` (once)
4. `POST /friends/add`
5. (Optional) `PATCH /friends/share-location` to control privacy
6. Towers → `POST /tower/pings` (with optional `status`)
7. Mobile → `GET /map/latest`
8. (Optional) `POST /incidents` to report safety threats

---

## Schema

### Users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, auto-generated |
| username | Text | Unique |
| password_hash | Text | Argon2 |
| display_name | Text | Nullable |
| profile_picture_url | Text | Nullable, must be Vercel Blob URL |
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
| status | Integer | 0=Safe, 1=Not Safe, 2=SOS. Default `0` |
| received_at | Timestamptz | Default `now()` |

### Incidents
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, auto-generated |
| reporter_id | UUID | FK → users |
| lat | Float | |
| lng | Float | |
| description | Text | |
| created_at | Timestamptz | Default `now()` |
