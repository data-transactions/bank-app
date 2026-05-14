"""add_token_version_status_block_fields_and_ledger_entries

Revision ID: a1b2c3d4e5f6
Revises: e7c4f7a7cdcc
Create Date: 2026-05-14 18:00:00

This migration adds:
  1. token_version, status, blocked_at, blocked_by, block_reason to `users`
  2. New `ledger_entries` table for append-only financial tracking
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e7c4f7a7cdcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add new columns to users ──
    op.add_column('users', sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'))
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('blocked_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('blocked_by', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('block_reason', sa.String(length=255), nullable=True))

    op.create_foreign_key(
        'fk_user_blocked_by',
        'users', 'users',
        ['blocked_by'], ['id'],
        use_alter=True
    )

    # ── 2. Create ledger_entries table ──
    op.create_table(
        'ledger_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('CREDIT', 'DEBIT', name='ledgertype'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('previous_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('new_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ledger_entries_id'), 'ledger_entries', ['id'], unique=False)
    op.create_index(op.f('ix_ledger_entries_user_id'), 'ledger_entries', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ledger_entries_user_id'), table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_id'), table_name='ledger_entries')
    op.drop_table('ledger_entries')
    try:
        op.drop_constraint('fk_user_blocked_by', 'users', type_='foreignkey')
    except Exception:
        pass
    op.drop_column('users', 'block_reason')
    op.drop_column('users', 'blocked_by')
    op.drop_column('users', 'blocked_at')
    op.drop_column('users', 'token_version')
    op.drop_column('users', 'status')
