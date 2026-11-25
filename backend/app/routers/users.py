from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.deps import get_current_user
from app.db.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update the authenticated user's profile."""
    user = AuthService(db).update_user(current_user, payload.name)
    return UserResponse.model_validate(user)
