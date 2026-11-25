from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.project import Project
    from app.db.models.skill import Skill
    from app.db.models.user import User


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="resumes")
    skills: Mapped[list[Skill]] = relationship(
        "Skill",
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="resume",
        cascade="all, delete-orphan",
    )
