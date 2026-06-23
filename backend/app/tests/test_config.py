import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_load_custom_values():
    """Verify settings can be loaded/overridden with custom parameters."""
    custom_settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        SECRET_KEY="another-secret",
        GEMINI_API_KEY="another-gemini-key",
        APP_NAME="Custom Exam App",
        APP_ENV="production",
        DEBUG=False,
        UPLOADS_DIR="/tmp/uploads",
    )
    assert custom_settings.APP_NAME == "Custom Exam App"
    assert custom_settings.APP_ENV == "production"
    assert custom_settings.DEBUG is False
    assert custom_settings.DATABASE_URL == "postgresql://user:pass@localhost:5432/db"
    assert custom_settings.SECRET_KEY == "another-secret"
    assert custom_settings.GEMINI_API_KEY == "another-gemini-key"
    assert custom_settings.UPLOADS_DIR == "/tmp/uploads"


def test_settings_missing_fields(monkeypatch):
    """Verify that settings validation fails and raises ValidationError when required fields are missing."""
    # Ensure environment variables are clear
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        # Pass _env_file=None to ignore the backend/.env file and system env
        Settings(_env_file=None)

    errors = exc_info.value.errors()
    missing_fields = {error["loc"][0] for error in errors}

    assert "DATABASE_URL" in missing_fields
    assert "SECRET_KEY" in missing_fields
