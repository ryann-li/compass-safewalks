import os


class Settings:
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXP_SECONDS: int
    TOWER_SHARED_KEY: str
    BLOB_READ_WRITE_TOKEN: str
    # TWILIO_ACCOUNT_SID: str
    # TWILIO_AUTH_TOKEN: str
    # TWILIO_FROM_NUMBER: str
    # SOS_ALERT_NUMBERS: list[str]

    def __init__(self) -> None:
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://safewalks:safewalks@localhost:5432/safewalks",
        )
        self.JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
        self.JWT_EXP_SECONDS = int(os.environ.get("JWT_EXP_SECONDS", "3600"))
        self.TOWER_SHARED_KEY = os.environ.get("TOWER_SHARED_KEY", "dev-tower-key")
        self.BLOB_READ_WRITE_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
        # Twilio configuration disabled
        # self.TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "YOUR_ACCOUNT_SID")
        # self.TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")
        # self.TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "YOUR_FROM_NUMBER")
        # SOS alert phone numbers (comma-separated in env var) 
        # numbers_str = os.environ.get("SOS_ALERT_NUMBERS", "YOUR_ALERT_NUMBERS")
        # self.SOS_ALERT_NUMBERS = [num.strip() for num in numbers_str.split(",") if num.strip()]


def get_settings() -> Settings:
    # Intentionally *not* cached so tests (and long-running processes)
    # can pick up env var changes such as TOWER_SHARED_KEY overrides.
    return Settings()

