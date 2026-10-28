import json
from typing import Any, List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "AI DevOps Assistant"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [i.strip() for i in v_stripped.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    POSTGRES_USER: str = "devops_user"
    POSTGRES_PASSWORD: str = "devops_password"
    POSTGRES_DB: str = "devops_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://devops_user:devops_password@localhost:5432/devops_db"

    # Multi-Cloud Deployment Providers
    RENDER_API_KEY: str = ""
    RENDER_SERVICE_ID: str = ""
    VERCEL_TOKEN: str = ""

    # Nebius AI Cloud & Multi-Model Serving
    NEBIUS_API_KEY: str = ""
    NEBIUS_BASE_URL: str = "https://api.studio.nebius.ai/v1"
    NEBIUS_API_BASE: Optional[str] = None
    DEEPSEEK_MODEL: str = "deepseek-ai/DeepSeek-V4.1-Flash"
    PREFERRED_FAST_MODEL: Optional[str] = None
    NEMOTRON_MODEL: str = "nvidia/Nemotron-3_5-Lightning"
    PREFERRED_REASONING_MODEL: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.NEBIUS_API_BASE and (not self.NEBIUS_BASE_URL or self.NEBIUS_BASE_URL == "https://api.studio.nebius.ai/v1"):
            self.NEBIUS_BASE_URL = self.NEBIUS_API_BASE
        if self.PREFERRED_FAST_MODEL and (not self.DEEPSEEK_MODEL or self.DEEPSEEK_MODEL == "deepseek-ai/DeepSeek-V4.1-Flash"):
            self.DEEPSEEK_MODEL = self.PREFERRED_FAST_MODEL
        if self.PREFERRED_REASONING_MODEL and (not self.NEMOTRON_MODEL or self.NEMOTRON_MODEL == "nvidia/Nemotron-3_5-Lightning"):
            self.NEMOTRON_MODEL = self.PREFERRED_REASONING_MODEL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
