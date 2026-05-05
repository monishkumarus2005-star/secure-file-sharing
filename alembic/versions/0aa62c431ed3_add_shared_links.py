"""add_shared_links

Revision ID: 0aa62c431ed3
Revises: 9a7fac3fbd83
Create Date: 2026-04-17 08:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0aa62c431ed3'
down_revision: Union[str, None] = '9a7fac3fbd83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make access_logs.user_id nullable to support public (anonymous) downloads.
    # Use batch mode for SQLite compatibility (SQLite does not support ALTER COLUMN directly).
    with op.batch_alter_table('access_logs', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            nullable=True
        )

    # Create shared_links table (skip if already exists for idempotency)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'shared_links' not in inspector.get_table_names():
        op.create_table(
            'shared_links',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('file_id', sa.Integer(), nullable=False),
            sa.Column('token', sa.String(length=64), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('max_downloads', sa.Integer(), nullable=True),
            sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('revoked', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(datetime(\'now\'))')),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_shared_links_id'), 'shared_links', ['id'], unique=False)
        op.create_index(op.f('ix_shared_links_file_id'), 'shared_links', ['file_id'], unique=False)
        op.create_index(op.f('ix_shared_links_token'), 'shared_links', ['token'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'shared_links' in inspector.get_table_names():
        op.drop_index(op.f('ix_shared_links_token'), table_name='shared_links')
        op.drop_index(op.f('ix_shared_links_file_id'), table_name='shared_links')
        op.drop_index(op.f('ix_shared_links_id'), table_name='shared_links')
        op.drop_table('shared_links')

    with op.batch_alter_table('access_logs', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            nullable=False
        )
