"""expand signing keys into a provider-backed registry

Revision ID: 0002_signing_key_registry
Revises: 0001_auth_skeleton
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_signing_key_registry"
down_revision: str | Sequence[str] | None = "0001_auth_skeleton"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("signing_keys", "key_reference", new_column_name="external_reference")
    op.alter_column(
        "signing_keys",
        "status",
        existing_type=sa.String(length=16),
        server_default="standby",
    )

    op.add_column(
        "signing_keys",
        sa.Column("provider_name", sa.String(length=64), server_default="legacy-primary", nullable=False),
    )
    op.add_column(
        "signing_keys",
        sa.Column("provider_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "signing_keys",
        sa.Column("purpose", sa.String(length=32), server_default="access_token", nullable=False),
    )
    op.add_column(
        "signing_keys",
        sa.Column("public_jwk", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "signing_keys",
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "signing_keys",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "signing_keys",
        sa.Column("unavailable_since", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("signing_keys", "retired_at", new_column_name="retiring_at")
    op.add_column(
        "signing_keys",
        sa.Column("retire_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "signing_keys",
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.drop_constraint("signing_key_status", "signing_keys", type_="check")
    op.execute("UPDATE signing_keys SET status = 'retiring' WHERE status = 'retired'")
    op.create_check_constraint(
        "signing_key_status",
        "signing_keys",
        "status IN ('standby', 'active', 'retiring', 'disabled')",
    )
    op.create_check_constraint(
        "signing_key_purpose",
        "signing_keys",
        "purpose IN ('access_token')",
    )

    op.create_index("ix_signing_keys_provider_name", "signing_keys", ["provider_name"], unique=False)
    op.create_index("ix_signing_keys_purpose", "signing_keys", ["purpose"], unique=False)
    op.create_unique_constraint(
        "uq_signing_keys_provider_reference_version",
        "signing_keys",
        ["provider_name", "external_reference", "provider_version"],
    )
    op.create_index(
        "uq_signing_keys_one_active_per_purpose_algorithm",
        "signing_keys",
        ["purpose", "algorithm"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.alter_column("signing_keys", "provider_name", server_default=None)
    op.alter_column("signing_keys", "provider_version", server_default=None)


def downgrade() -> None:
    op.drop_index("uq_signing_keys_one_active_per_purpose_algorithm", table_name="signing_keys")
    op.drop_constraint("uq_signing_keys_provider_reference_version", "signing_keys", type_="unique")
    op.drop_index("ix_signing_keys_purpose", table_name="signing_keys")
    op.drop_index("ix_signing_keys_provider_name", table_name="signing_keys")

    op.drop_constraint("signing_key_purpose", "signing_keys", type_="check")
    op.drop_constraint("signing_key_status", "signing_keys", type_="check")
    op.execute(
        "UPDATE signing_keys SET status = 'retired' "
        "WHERE status IN ('standby', 'retiring', 'disabled')"
    )
    op.create_check_constraint(
        "signing_key_status",
        "signing_keys",
        "status IN ('active', 'retired')",
    )

    op.drop_column("signing_keys", "disabled_at")
    op.drop_column("signing_keys", "retire_after")
    op.alter_column("signing_keys", "retiring_at", new_column_name="retired_at")
    op.drop_column("signing_keys", "unavailable_since")
    op.drop_column("signing_keys", "last_seen_at")
    op.drop_column("signing_keys", "discovered_at")
    op.drop_column("signing_keys", "public_jwk")
    op.drop_column("signing_keys", "purpose")
    op.drop_column("signing_keys", "provider_version")
    op.drop_column("signing_keys", "provider_name")

    op.alter_column(
        "signing_keys",
        "status",
        existing_type=sa.String(length=16),
        server_default="active",
    )
    op.alter_column("signing_keys", "external_reference", new_column_name="key_reference")
