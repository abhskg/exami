from fastapi import APIRouter, Depends

from app.api.auth_dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve the current authenticated user's details.
    """
    return current_user
