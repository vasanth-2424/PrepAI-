from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.interview_session import InterviewSession


class SessionAnswer(Base):
    __tablename__ = "session_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalized: store the question text so results are immutable even
    # if the generated questions are re-generated later.
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Category / metadata stored as plain text for the same reason
    question_category: Mapped[str] = mapped_column(Text, nullable=False, default="")
    question_difficulty: Mapped[str] = mapped_column(Text, nullable=False, default="")
    question_type: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Help system tracking (JSON array string e.g. ["small_hint", "explain_concept"])
    assistance_used: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Evaluation fields (nullable until evaluated)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adjusted_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    technical_accuracy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clarity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completeness: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    session: Mapped[InterviewSession] = relationship(
        "InterviewSession", back_populates="answers"
    )
