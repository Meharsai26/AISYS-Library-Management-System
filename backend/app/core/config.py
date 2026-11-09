from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AISYS Library Management System"
    app_env: str = "development"
    database_url: str = "sqlite:///./library_demo.sqlite3"

    session_idle_minutes: int = 15
    session_absolute_minutes: int = 60

    max_loan_renewals: int = Field(default=2, ge=0)
    loan_renewal_days: int = Field(default=14, ge=1)

    max_fine_paise: int = Field(default=50000, ge=0)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
