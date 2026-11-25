from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.exceptions import AppException
from app.utils.security import create_access_token, hash_password, verify_password


class AuthService:
    """Handles user registration, authentication, and profile updates."""

    def __init__(self, db: Session):
        self._db = db

    def register(self, payload: RegisterRequest, settings: Settings) -> tuple[User, str]:
        if self.get_user_by_email(payload.email) is not None:
            raise AppException("Email already registered", status_code=409)

        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)

        token = create_access_token(subject=str(user.id), settings=settings)
        return user, token

    def login(self, payload: LoginRequest, settings: Settings) -> tuple[User, str]:
        user = self.get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AppException("Invalid email or password", status_code=401)

        token = create_access_token(subject=str(user.id), settings=settings)
        return user, token

    def get_user_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_user_by_email(self, email: str) -> User | None:
        return self._db.scalar(select(User).where(User.email == email))

    def update_user(self, user: User, name: str) -> User:
        user.name = name
        self._db.commit()
        self._db.refresh(user)
        return user
