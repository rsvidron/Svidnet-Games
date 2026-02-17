"""
Core configuration module
Loads settings from environment variables
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List
import secrets


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "SvidNet Game Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://gameuser:gamepass@localhost:5432/gamedb",
        description="PostgreSQL connection string"
    )
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT encoding"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173"
    ]
    ALLOWED_HOSTS: List[str] = ["*"]

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # AI Integration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-pro"
    AI_GENERATION_MAX_TOKENS: int = 2048

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000

    # Game Settings
    DAILY_WORDLE_RESET_HOUR: int = 0
    DEFAULT_ELO_RATING: int = 1200
    TRIVIA_TIME_LIMIT_SECONDS: int = 30
    JEOPARDY_BUZZ_WINDOW_MS: int = 3000

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = ["csv", "json"]

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@svidnet.com"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # External APIs - The Odds API
    ODDS_API_KEY: str = ""
    ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"
    ODDS_CACHE_TTL_SECONDS: int = 300  # 5 minutes cache for live odds

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
