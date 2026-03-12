"""add_first_last_name

Revision ID: a1b2c3d4e5f6
Revises: f7dff682f99f
Create Date: 2026-03-12 09:26:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f7dff682f99f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if first_name column already exists; if not, add it.
    # We use a try/except approach via batch_alter_table for compatibility.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [col['name'] for col in insp.get_columns('users')]

    if 'first_name' not in columns:
        op.add_column('users', sa.Column('first_name', sa.String(50), nullable=True))
    if 'last_name' not in columns:
        op.add_column('users', sa.Column('last_name', sa.String(50), nullable=True))

    # If full_name exists, migrate data then drop it
    if 'full_name' in columns:
        # Split existing full_name into first_name and last_name
        op.execute(
            "UPDATE users SET "
            "first_name = TRIM(SUBSTRING_INDEX(full_name, ' ', 1)), "
            "last_name = TRIM(SUBSTRING(full_name, LOCATE(' ', full_name) + 1)) "
            "WHERE full_name IS NOT NULL"
        )
        # Fallback: if last_name is empty (single-word name), copy first_name
        op.execute(
            "UPDATE users SET last_name = first_name "
            "WHERE (last_name IS NULL OR last_name = '') AND first_name IS NOT NULL"
        )
        op.drop_column('users', 'full_name')

    # Make the columns NOT NULL now that data has been populated
    op.alter_column('users', 'first_name', nullable=False, existing_type=sa.String(50))
    op.alter_column('users', 'last_name', nullable=False, existing_type=sa.String(50))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [col['name'] for col in insp.get_columns('users')]

    if 'full_name' not in columns:
        op.add_column('users', sa.Column('full_name', sa.String(150), nullable=True))
        op.execute(
            "UPDATE users SET full_name = CONCAT(first_name, ' ', last_name)"
        )
        op.alter_column('users', 'full_name', nullable=False, existing_type=sa.String(150))

    if 'first_name' in columns:
        op.drop_column('users', 'first_name')
    if 'last_name' in columns:
        op.drop_column('users', 'last_name')
