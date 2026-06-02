"""merge_v096_and_fork_heads

Revision ID: 2819b55acfd3
Revises: 461111b60977, e6f7a8b9c0d1
Create Date: 2026-06-02 08:46:30.605286

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

# revision identifiers, used by Alembic.
revision: str = '2819b55acfd3'
down_revision: Union[str, None] = ('461111b60977', 'e6f7a8b9c0d1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
