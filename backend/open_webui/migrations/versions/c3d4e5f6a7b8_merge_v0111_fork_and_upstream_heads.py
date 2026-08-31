"""merge_v0111_fork_and_upstream_heads

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6, d4c1a8e37b62
Create Date: 2026-08-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = ('b1c2d3e4f5a6', 'd4c1a8e37b62')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
