import os


class Settings:
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXP_SECONDS: int
    TOWER_SHARED_KEY: str

    def __init__(self) -> None:
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://safewalks:safewalks@localhost:5432/safewalks",
        )
        self.JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
        self.JWT_EXP_SECONDS = int(os.environ.get("JWT_EXP_SECONDS", "3600"))
        self.TOWER_SHARED_KEY = os.environ.get("TOWER_SHARED_KEY", "dev-tower-key")


def get_settings() -> Settings:
    # Intentionally *not* cached so tests (and long-running processes)
    # can pick up env var changes such as TOWER_SHARED_KEY overrides.
    return Settings()

