"""Merge legacy auth history into the local-only schema.

Revision ID: 004_local_only_root
Revises: 003_org_acronym, 002_user_topic_ownership
Create Date: 2026-03-15

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_local_only_root"
down_revision: Union[str, Sequence[str], None] = (
    "003_org_acronym",
    "002_user_topic_ownership",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE bronze.raw_govuk_items "
        "ALTER COLUMN content_id TYPE VARCHAR(512)"
    )
    op.execute(
        "ALTER TABLE silver.content_items "
        "ALTER COLUMN content_id TYPE VARCHAR(512)"
    )
    op.execute(
        "ALTER TABLE silver.organisations "
        "ALTER COLUMN acronym TYPE VARCHAR(256)"
    )

    op.execute("DROP TABLE IF EXISTS silver.topic_memberships CASCADE")
    op.execute("DROP TABLE IF EXISTS silver.users CASCADE")

    op.execute("ALTER TABLE silver.topics DROP CONSTRAINT IF EXISTS ck_topics_scope_owner")
    op.execute("ALTER TABLE silver.topics DROP CONSTRAINT IF EXISTS fk_topics_owner_user_id")
    op.execute("DROP INDEX IF EXISTS silver.ix_topics_owner_user_id")
    op.execute("DROP INDEX IF EXISTS silver.uq_topics_slug_global")
    op.execute("DROP INDEX IF EXISTS silver.uq_topics_owner_slug_private")
    op.execute("ALTER TABLE silver.topics DROP COLUMN IF EXISTS owner_user_id")

    op.execute("ALTER TABLE silver.topics DROP CONSTRAINT IF EXISTS topics_slug_key")
    op.execute("DROP INDEX IF EXISTS silver.ix_topics_slug")
    op.execute(
        "ALTER TABLE silver.topics "
        "ADD CONSTRAINT topics_slug_key UNIQUE (slug)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_topics_slug "
        "ON silver.topics (slug)"
    )


def downgrade() -> None:
    pass