"""create_jwt_table

Revision ID: c686ddddf3f0
Revises: 
Create Date: 2026-04-21 16:18:59.383569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c686ddddf3f0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create signing_keys table
    op.create_table(
        'signing_keys',
        sa.Column('kid', sa.Text(), nullable=False),
        sa.Column('algorithm', sa.Text(), nullable=False),
        sa.Column('public_key_pem', sa.Text(), nullable=False),
        sa.Column('private_key_pem', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('kid'),
        sa.CheckConstraint("status IN ('active','retired')", name='ck_status')
    )    
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('signing_keys')
