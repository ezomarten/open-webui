"""merge_fork_memory_and_v096_merge

Revision ID: a9f3c7e2b1d4
Revises: 2819b55acfd3, 42e2978c7933
Create Date: 2026-07-11 21:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

revision: str = 'a9f3c7e2b1d4'
down_revision: Union[str, None] = ('2819b55acfd3', '42e2978c7933')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
