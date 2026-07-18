"""create auth skeleton

Revision ID: 0001_auth_skeleton
Revises:
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_auth_skeleton"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="user", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "role IN ('user', 'moderator', 'admin')",
            name="user_role",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "signing_keys",
        sa.Column("kid", sa.String(length=128), nullable=False),
        sa.Column("backend", sa.String(length=16), nullable=False),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("key_reference", sa.String(length=255), nullable=False),
        sa.Column("public_key_pem", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "backend IN ('local', 'vault')",
            name="signing_backend",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'retired')",
            name="signing_key_status",
        ),
        sa.PrimaryKeyConstraint("kid", name="pk_signing_keys"),
    )
    op.create_index("ix_signing_keys_backend", "signing_keys", ["backend"], unique=False)
    op.create_index("ix_signing_keys_status", "signing_keys", ["status"], unique=False)

    op.create_table(
        "device_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("device_name", sa.String(length=200), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("client_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_device_sessions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_device_sessions"),
    )
    op.create_index("ix_device_sessions_device_id", "device_sessions", ["device_id"], unique=False)
    op.create_index("ix_device_sessions_expires_at", "device_sessions", ["expires_at"], unique=False)
    op.create_index("ix_device_sessions_revoked_at", "device_sessions", ["revoked_at"], unique=False)
    op.create_index("ix_device_sessions_user_device", "device_sessions", ["user_id", "device_id"], unique=False)
    op.create_index("ix_device_sessions_user_id", "device_sessions", ["user_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_session_id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["device_session_id"],
            ["device_sessions.id"],
            name="fk_refresh_tokens_device_session_id_device_sessions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"],
            ["refresh_tokens.id"],
            name="fk_refresh_tokens_replaced_by_id_refresh_tokens",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("replaced_by_id", name="uq_refresh_tokens_replaced_by_id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_device_session_id", "refresh_tokens", ["device_session_id"], unique=False)
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"], unique=False)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"], unique=False)
    op.create_index("ix_refresh_tokens_revoked_at", "refresh_tokens", ["revoked_at"], unique=False)
    op.create_index(
        "ix_refresh_tokens_session_family",
        "refresh_tokens",
        ["device_session_id", "family_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_session_family", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_revoked_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_device_session_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_device_sessions_user_id", table_name="device_sessions")
    op.drop_index("ix_device_sessions_user_device", table_name="device_sessions")
    op.drop_index("ix_device_sessions_revoked_at", table_name="device_sessions")
    op.drop_index("ix_device_sessions_expires_at", table_name="device_sessions")
    op.drop_index("ix_device_sessions_device_id", table_name="device_sessions")
    op.drop_table("device_sessions")

    op.drop_index("ix_signing_keys_status", table_name="signing_keys")
    op.drop_index("ix_signing_keys_backend", table_name="signing_keys")
    op.drop_table("signing_keys")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
