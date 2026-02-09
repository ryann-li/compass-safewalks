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
| GET | `/friends` | - | 200: `{ friends: [...] }` |


### Tower Ingestion *(Tower key required)*
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/tower/pings` | `{ fob_uid, lat, lng }` | 201: `{ stored }` / 401 TOWER_UNAUTHORIZED |

> Fobs are auto-registered on first tower ping if they don't already exist.



### Map *(JWT required)*
| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/map/latest?window_minutes=10` | 200: `{ window_minutes, results: [{ friend, fob_uid, location: { lat, lng, received_at } }] }` |

---

## Client Flow

1. `POST /auth/signup` or `/auth/login` → JWT
2. `POST /fob/claim` (once)
3. `POST /friends/add`
4. Towers → `POST /tower/pings`
5. Mobile → `GET /map/latest`
