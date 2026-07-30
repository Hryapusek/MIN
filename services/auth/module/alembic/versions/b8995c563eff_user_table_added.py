"""User table added

Revision ID: b8995c563eff
Revises: ebb6c2988c9a
Create Date: 2026-07-30 12:39:36.500130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8995c563eff'
down_revision: Union[str, Sequence[str], None] = 'ebb6c2988c9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.schema.CreateSchema("auth"))
    op.execute(sa.schema.CreateSchema("key_management"))

    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('surname', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('role', sa.Enum('user', 'moderator', 'admin', name='user_role', native_enum=False, create_constraint=True), server_default='user', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('banned_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('false'), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    schema='auth'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('users', schema='auth')

    op.execute(sa.schema.DropSchema("key_management"))
    op.execute(sa.schema.DropSchema("auth"))
