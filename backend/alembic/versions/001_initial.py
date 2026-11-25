"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resumes_id"), "resumes", ["id"], unique=False)
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"], unique=False)

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_questions_id"), "interview_questions", ["id"], unique=False)
    op.create_index(op.f("ix_interview_questions_user_id"), "interview_questions", ["user_id"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("project_name", sa.String(length=512), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(op.f("ix_projects_resume_id"), "projects", ["resume_id"], unique=False)

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skills_id"), "skills", ["id"], unique=False)
    op.create_index(op.f("ix_skills_resume_id"), "skills", ["resume_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_skills_resume_id"), table_name="skills")
    op.drop_index(op.f("ix_skills_id"), table_name="skills")
    op.drop_table("skills")
    op.drop_index(op.f("ix_projects_resume_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_interview_questions_user_id"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_id"), table_name="interview_questions")
    op.drop_table("interview_questions")
    op.drop_index(op.f("ix_resumes_user_id"), table_name="resumes")
    op.drop_index(op.f("ix_resumes_id"), table_name="resumes")
    op.drop_table("resumes")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
