"""Add auth and profile fields to users.

Revision ID: 20260506a001
Revises:
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260506a001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=30), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), server_default="youth", nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "role")
    op.drop_column("users", "phone")
    op.drop_column("users", "email")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
