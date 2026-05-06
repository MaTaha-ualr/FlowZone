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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "username" not in columns:
        op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    if "password_hash" not in columns:
        op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    if "email" not in columns:
        op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    if "phone" not in columns:
        op.add_column("users", sa.Column("phone", sa.String(length=30), nullable=True))
    if "role" not in columns:
        op.add_column(
            "users",
            sa.Column("role", sa.String(length=20), server_default="youth", nullable=False),
        )

    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_username" not in indexes:
        op.create_index("ix_users_username", "users", ["username"], unique=True)
    if "ix_users_email" not in indexes:
        op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_email" in indexes:
        op.drop_index("ix_users_email", table_name="users")
    if "ix_users_username" in indexes:
        op.drop_index("ix_users_username", table_name="users")

    columns = {column["name"] for column in inspector.get_columns("users")}
    for column in ("role", "phone", "email", "password_hash", "username"):
        if column in columns:
            op.drop_column("users", column)
