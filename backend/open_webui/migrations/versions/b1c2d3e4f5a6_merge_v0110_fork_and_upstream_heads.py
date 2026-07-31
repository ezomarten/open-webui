"""merge_v0110_fork_and_upstream_heads

Revision ID: b1c2d3e4f5a6
Revises: a9f3c7e2b1d4, f0bd01a18a3d
Create Date: 2026-07-31 23:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = ("a9f3c7e2b1d4", "f0bd01a18a3d")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass