"""Add public_share table

Revision ID: 9c0d8a1b2e3f
Revises: b2c3d4e5f6a7
Create Date: 2026-03-15 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = '9c0d8a1b2e3f'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if 'public_share' not in existing_tables:
        op.create_table(
            'public_share',
            sa.Column('id', sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column('chat_id', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('title', sa.Text(), nullable=False),
            sa.Column('snapshot_json', sa.JSON(), nullable=False),
            sa.Column('message_count', sa.Integer(), nullable=False),
            sa.Column('source_chat_updated_at', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('chat_id', name='uq_public_share_chat_id'),
        )
        op.create_index(
            'public_share_user_updated_idx',
            'public_share',
            ['user_id', 'updated_at'],
        )


def downgrade() -> None:
    op.drop_index('public_share_user_updated_idx', table_name='public_share')
    op.drop_table('public_share')
