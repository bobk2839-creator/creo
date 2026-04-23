import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "fueluser"
    POSTGRES_PASSWORD: str = "fuelpass123"
    POSTGRES_DB: str = "fuelprocess"
    DATABASE_URL: str = "postgresql+asyncpg://fueluser:fuelpass123@localhost:5432/fuelprocess"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Application
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "FuelProcess SaaS"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 50

    # OpenRouteService API Key
    OPENROUTESERVICE_API_KEY: str = ""

    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
