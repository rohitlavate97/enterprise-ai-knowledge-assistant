"""Application configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core Application Settings
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Storage Settings
    UPLOAD_DIR: str = "storage/documents"

    # Security & Authentication
    JWT_SECRET_KEY: str = "supersecretjwtkeyplaceholderchangeinproduction"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Relational Database (MySQL 8.4 LTS)
    DATABASE_URL: str = (
        "mysql+aiomysql://root:password@localhost:3306/knowledge_assistant"
    )

    # Caching & Session Storage (Redis)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Message Broker & Task Queue (RabbitMQ / Celery)
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Vector Database (Qdrant)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""

    # LLM Providers (OpenAI is default)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"


settings = Settings()
