import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from api.index import app
from app.settings import get_settings, Settings


_raw_test_db_url = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://safewalks:safewalks@localhost:5432/safewalks",
    ),
)

# Normalize URL to include psycopg2 driver if missing (for Alembic compatibility)
if _raw_test_db_url.startswith("postgresql://") and "+psycopg2" not in _raw_test_db_url:
    TEST_DB_URL = _raw_test_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    TEST_DB_URL = _raw_test_db_url


class TestSettings(Settings):
    def __init__(self) -> None:
        super().__init__()
        self.DATABASE_URL = TEST_DB_URL


def override_settings() -> Settings:
    return TestSettings()


app.dependency_overrides[get_settings] = override_settings


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def setup_db() -> None:
    # Ensure env var used by alembic.ini if needed
    os.environ["DATABASE_URL"] = TEST_DB_URL
    run_migrations()


# Engine for direct cleanup between tests
_engine = create_engine(TEST_DB_URL)


@pytest.fixture(autouse=True)
def clean_db() -> None:
    """Ensure a clean DB state before each test (except seeded towers)."""
    with _engine.begin() as conn:
        # Order matters less with CASCADE; leave towers as seeded.
        conn.execute(
            text(
                "TRUNCATE TABLE pings, friendships, fobs, users RESTART IDENTITY CASCADE;"
            )
        )


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c

