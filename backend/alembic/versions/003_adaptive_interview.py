"""Add mode, final_report, assistance_used, raw_score, adjusted_score columns

Revision ID: 003_adaptive_interview
Revises: 002_interview_sessions
Create Date: 2026-09-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_adaptive_interview"
down_revision: Union[str, None] = "002_interview_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("mode", sa.String(length=50), nullable=False, server_default="standard"),
    )
    op.add_column(
        "interview_sessions",
        sa.Column("final_report", sa.Text(), nullable=True),
    )

    op.add_column(
        "session_answers",
        sa.Column("assistance_used", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "session_answers",
        sa.Column("raw_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "session_answers",
        sa.Column("adjusted_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_answers", "adjusted_score")
    op.drop_column("session_answers", "raw_score")
    op.drop_column("session_answers", "assistance_used")
    op.drop_column("interview_sessions", "final_report")
    op.drop_column("interview_sessions", "mode")
