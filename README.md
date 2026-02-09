## Compass SafeWalks Backend (v1)

Minimal FastAPI backend for Compass SafeWalks, serving both mobile clients and hardware towers.

### Requirements

- Python 3.x
- PostgreSQL (see below)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Start Postgres

You need a running PostgreSQL instance. Pick **one** of these options:

**Option A — Homebrew (no Docker needed):**

```bash
brew install postgresql@16
brew services start postgresql@16
createuser -s safewalks
createdb -U safewalks safewalks
```

**Option B — [Postgres.app](https://postgresapp.com/) (no Docker needed):**

Download, launch, and create the database:

```bash
createuser -s safewalks
createdb -U safewalks safewalks
```

**Option C — Docker:**

```bash
docker compose up -d db
```

The default database URL is:

```text
postgresql+psycopg2://safewalks:safewalks@localhost:5432/safewalks
```

Configure env vars (example `.env` or shell):

```bash
export DATABASE_URL="postgresql+psycopg2://safewalks:safewalks@localhost:5432/safewalks"
export JWT_SECRET="change-me"
export TOWER_SHARED_KEY="dev-tower-key"
export JWT_EXP_SECONDS=3600
```

### Run migrations

```bash
alembic upgrade head
```

This creates all tables and seeds the two default towers (`tower-1`, `tower-2`).

### Run the API server

```bash
uvicorn api.index:app --reload
```

The health check is at `GET /health`.

### Run tests

Ensure the database is running, and (optionally) point tests at a dedicated DB via `TEST_DATABASE_URL`:

```bash
export TEST_DATABASE_URL="postgresql+psycopg2://safewalks:safewalks@localhost:5432/safewalks_test"
pytest
```

Tests will automatically run Alembic migrations against the configured test database and verify:

- Core happy-path flow (signup/login, friends, fobs, tower ping, map/latest)
- Mutual friends invariant
- Tower auth enforcement
- Fob uniqueness

