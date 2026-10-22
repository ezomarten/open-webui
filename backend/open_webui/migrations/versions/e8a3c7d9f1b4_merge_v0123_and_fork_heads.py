"""merge_v0123_and_fork_heads

Revision ID: e8a3c7d9f1b4
Revises: c3d4e5f6a7b8, 0bd252b206fb
Create Date: 2026-10-21 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

revision: str = 'e8a3c7d9f1b4'
down_revision: Union[str, None] = ('c3d4e5f6a7b8', '0bd252b206fb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
