from datetime import datetime, timedelta, timezone

import pytest
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password


def test_password_hashing():
    """Verify that password hashing and verification work as expected."""
    password = "super-secret-password-123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_access_token():
    """Verify that access token has correct subject and expiration."""
    subject = "user-12345"
    token = create_access_token(subject=subject)

    # Decode and verify contents
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload.get("sub") == subject
    assert "exp" in payload


def test_create_access_token_custom_expiry():
    """Verify that token respects a custom expiration time."""
    subject = "user-54321"
    custom_expiry = timedelta(minutes=5)
    token = create_access_token(subject=subject, expires_delta=custom_expiry)

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload.get("sub") == subject

    # exp is a UNIX timestamp
    exp_timestamp = payload.get("exp")
    now_timestamp = datetime.now(timezone.utc).timestamp()

    # Expiry should be roughly 5 minutes (300 seconds) in the future
    time_diff = exp_timestamp - now_timestamp
    assert 290 <= time_diff <= 310
