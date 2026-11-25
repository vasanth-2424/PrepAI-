from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.interview_question import InterviewQuestion
    from app.db.models.interview_session import InterviewSession
    from app.db.models.resume import Resume


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    resumes: Mapped[list[Resume]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    interview_questions: Mapped[list[InterviewQuestion]] = relationship(
        "InterviewQuestion",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    interview_sessions: Mapped[list[InterviewSession]] = relationship(
        "InterviewSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
