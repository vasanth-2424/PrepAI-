"""Add interview_sessions and session_answers tables

Revision ID: 002_interview_sessions
Revises: 001_initial
Create Date: 2026-09-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_interview_sessions"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="in_progress"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_sessions_id"), "interview_sessions", ["id"], unique=False)
    op.create_index(
        op.f("ix_interview_sessions_user_id"), "interview_sessions", ["user_id"], unique=False
    )

    op.create_table(
        "session_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_category", sa.Text(), nullable=False, server_default=""),
        sa.Column("question_difficulty", sa.Text(), nullable=False, server_default=""),
        sa.Column("question_type", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("technical_accuracy", sa.Text(), nullable=True),
        sa.Column("clarity", sa.Text(), nullable=True),
        sa.Column("completeness", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("suggested_answer", sa.Text(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_session_answers_id"), "session_answers", ["id"], unique=False)
    op.create_index(
        op.f("ix_session_answers_session_id"), "session_answers", ["session_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_session_answers_session_id"), table_name="session_answers")
    op.drop_index(op.f("ix_session_answers_id"), table_name="session_answers")
    op.drop_table("session_answers")
    op.drop_index(op.f("ix_interview_sessions_user_id"), table_name="interview_sessions")
    op.drop_index(op.f("ix_interview_sessions_id"), table_name="interview_sessions")
    op.drop_table("interview_sessions")
