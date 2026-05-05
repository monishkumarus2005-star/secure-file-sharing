"""redesign_share_links

Revision ID: d41614c09bbd
Revises: 0aa62c431ed3
Create Date: 2026-04-17 09:30:15.569995+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd41614c09bbd'
down_revision = '0aa62c431ed3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create share_links table
    op.create_table('share_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.Column('token', sa.String(length=64), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('max_uses', sa.Integer(), nullable=False),
    sa.Column('use_count', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_share_links_file_id'), 'share_links', ['file_id'], unique=False)
    op.create_index(op.f('ix_share_links_id'), 'share_links', ['id'], unique=False)
    op.create_index(op.f('ix_share_links_token'), 'share_links', ['token'], unique=True)
    
    # Drop shared_links table (added in previous session but now replaced)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'shared_links' in inspector.get_table_names():
        op.drop_index('ix_shared_links_file_id', table_name='shared_links')
        op.drop_index('ix_shared_links_id', table_name='shared_links')
        op.drop_index('ix_shared_links_token', table_name='shared_links')
        op.drop_table('shared_links')

    # Batch alter for SQLite compatibility
    with op.batch_alter_table('access_logs', schema=None) as batch_op:
        batch_op.alter_column('access_time',
               existing_type=sa.DATETIME(),
               nullable=False,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))

    with op.batch_alter_table('files', schema=None) as batch_op:
        batch_op.alter_column('upload_time',
               existing_type=sa.DATETIME(),
               nullable=False,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
        batch_op.alter_column('processing_status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=False,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=True,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))
    
    with op.batch_alter_table('files', schema=None) as batch_op:
        batch_op.alter_column('processing_status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)
        batch_op.alter_column('upload_time',
               existing_type=sa.DATETIME(),
               nullable=True,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))

    with op.batch_alter_table('access_logs', schema=None) as batch_op:
        batch_op.alter_column('access_time',
               existing_type=sa.DATETIME(),
               nullable=True,
               existing_server_default=sa.text('(CURRENT_TIMESTAMP)'))

    op.drop_index(op.f('ix_share_links_token'), table_name='share_links')
    op.drop_index(op.f('ix_share_links_id'), table_name='share_links')
    op.drop_index(op.f('ix_share_links_file_id'), table_name='share_links')
    op.drop_table('share_links')
