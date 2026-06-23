import os
import sys
from pathlib import Path
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve backend directory dynamically relative to this file
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"

class Settings(BaseSettings):
    # App Configuration
    APP_NAME: str = "AI-Powered Exam Preparation Portal"
    APP_ENV: str = "local"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

    # Database Configuration (PostgreSQL + pgvector)
    DATABASE_URL: str
    EMBEDDING_DIMENSION: int = 768

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # LLM Provider Configuration
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-2.0-flash"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LMSTUDIO_BASE_URL: str = "http://localhost:1234/v1"

    # Embedding Provider Configuration
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""

    # Storage Settings
    UPLOADS_DIR: str = "./data/uploads"

    model_config = SettingsConfigDict(
        # Load from backend/.env if present, otherwise fallback to system environment variables
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate and validate settings at import time
try:
    settings = Settings()
except ValidationError as e:
    print("Configuration validation failed. Please check your environment variables or .env file.", file=sys.stderr)
    for error in e.errors():
        loc = " -> ".join(str(loc) for loc in error.get("loc", []))
        print(f"  - {loc}: {error.get('msg')}", file=sys.stderr)
    sys.exit(1)
