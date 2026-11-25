from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.session_answer import SessionAnswer
    from app.db.models.user import User


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="in_progress"
    )
    mode: Mapped[str] = mapped_column(
        String(50), nullable=False, default="standard"
    )
    final_report: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship("User", back_populates="interview_sessions")
    answers: Mapped[list[SessionAnswer]] = relationship(
        "SessionAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionAnswer.id",
    )
