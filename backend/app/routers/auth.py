from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.deps import get_current_user
from app.db.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    """Register a new user and return an access token."""
    user, token = AuthService(db).register(payload, settings)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Authenticate a user and return an access token."""
    _, token = AuthService(db).login(payload, settings)
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)
