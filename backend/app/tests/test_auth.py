import pytest
from fastapi import status

from app.core.security import verify_password
from app.models.user import User


def test_register_user_success(client, db):
    """Verify that a new user is successfully registered and saved to database."""
    email = "newuser@example.com"
    password = "password123"
    display_name = "New User"

    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == email
    assert data["display_name"] == display_name
    assert "id" in data
    assert data["plan_tier"] == "free"

    # Check that user is in DB and password is hashed
    db_user = db.query(User).filter(User.email == email).first()
    assert db_user is not None
    assert db_user.display_name == display_name
    assert db_user.password_hash != password
    assert verify_password(password, db_user.password_hash) is True


def test_register_user_duplicate_email(client, db):
    """Verify registration fails with 400 when registering an already registered email."""
    email = "dupuser@example.com"
    password = "password123"

    # Register first time
    response1 = client.post("/api/auth/register", json={"email": email, "password": password})
    assert response1.status_code == status.HTTP_201_CREATED

    # Register second time
    response2 = client.post("/api/auth/register", json={"email": email, "password": password})
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response2.json()["detail"]


def test_register_user_short_password(client):
    """Verify Pydantic password length validation works."""
    response = client.post(
        "/api/auth/register", json={"email": "shortpwd@example.com", "password": "123"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_user_success(client, db):
    """Verify successful authentication returns a valid JWT token."""
    email = "loginuser@example.com"
    password = "secretpassword"

    # Register the user first
    register_response = client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert register_response.status_code == status.HTTP_201_CREATED

    # Attempt login
    login_response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == status.HTTP_200_OK
    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


def test_login_user_incorrect_credentials(client):
    """Verify login fails with 400 for incorrect email or password."""
    email = "loginfail@example.com"

    # Try logging in to non-existent user
    response = client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Incorrect email or password" in response.json()["detail"]
