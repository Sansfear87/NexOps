from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "AI DevOps Assistant"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    POSTGRES_USER: str = "devops_user"
    POSTGRES_PASSWORD: str = "devops_password"
    POSTGRES_DB: str = "devops_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://devops_user:devops_password@localhost:5432/devops_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
