import pytest
from fastapi import status
from datetime import timedelta
from app.core.security import create_access_token
from app.models.user import User

def test_get_current_user_success(client, db):
    """Verify that current user is correctly resolved from a valid JWT token."""
    email = "depsuser@example.com"
    password = "password123"
    
    # Register the user
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password}
    )
    
    # Login to get the token
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    
    # Access protected /users/me endpoint using token in header
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/users/me", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == email

def test_get_current_user_no_token(client):
    """Verify accessing protected endpoint without a token raises 401."""
    response = client.get("/api/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"]

def test_get_current_user_invalid_token(client):
    """Verify accessing protected endpoint with an invalid token raises 401."""
    headers = {"Authorization": "Bearer invalidtoken123"}
    response = client.get("/api/users/me", headers=headers)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"]

def test_get_current_user_expired_token(client, db):
    """Verify accessing protected endpoint with an expired token raises 401."""
    # Create user
    db_user = User(
        email="expired@example.com",
        password_hash="dummy_hash",
        plan_tier="free"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create an access token that is already expired (e.g. -1 minute)
    token = create_access_token(subject=db_user.id, expires_delta=timedelta(minutes=-1))
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/users/me", headers=headers)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"]
