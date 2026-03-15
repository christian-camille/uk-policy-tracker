"""Legacy revision retained as a no-op compatibility marker.

Revision ID: 002_user_topic_ownership
Revises: 001_initial_schema
Create Date: 2026-03-03

This repository is now local-only, so the old user/topic ownership schema is
not part of fresh installs anymore. The revision ID is kept so existing
databases that were stamped with the legacy history can still upgrade.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "002_user_topic_ownership"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass