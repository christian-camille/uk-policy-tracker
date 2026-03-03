"""Add user ownership and topic memberships

Revision ID: 002_user_topic_ownership
Revises: 001_initial_schema
Create Date: 2026-03-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_user_topic_ownership"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("auth_provider", sa.String(32), nullable=False, server_default="supabase"),
        sa.Column("provider_subject", sa.String(128), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("display_name", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint(
            "auth_provider",
            "provider_subject",
            name="uq_users_provider_subject",
        ),
        schema="silver",
    )
    op.create_index(
        "ix_users_provider_subject",
        "users",
        ["provider_subject"],
        unique=True,
        schema="silver",
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True, schema="silver")

    op.add_column(
        "topics",
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema="silver",
    )
    op.add_column(
        "topics",
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        schema="silver",
    )
    op.create_foreign_key(
        "fk_topics_owner_user_id",
        "topics",
        "users",
        ["owner_user_id"],
        ["id"],
        source_schema="silver",
        referent_schema="silver",
    )
    op.create_index("ix_topics_owner_user_id", "topics", ["owner_user_id"], schema="silver")

    op.execute("ALTER TABLE silver.topics DROP CONSTRAINT IF EXISTS topics_slug_key")
    op.execute("DROP INDEX IF EXISTS silver.ix_topics_slug")
    op.create_index("ix_topics_slug", "topics", ["slug"], schema="silver")
    op.create_index(
        "uq_topics_slug_global",
        "topics",
        ["slug"],
        unique=True,
        schema="silver",
        postgresql_where=sa.text("is_global"),
    )
    op.create_index(
        "uq_topics_owner_slug_private",
        "topics",
        ["owner_user_id", "slug"],
        unique=True,
        schema="silver",
        postgresql_where=sa.text("NOT is_global"),
    )

    op.create_check_constraint(
        "ck_topics_scope_owner",
        "topics",
        "(is_global = true AND owner_user_id IS NULL) OR (is_global = false AND owner_user_id IS NOT NULL)",
        schema="silver",
    )

    op.create_table(
        "topic_memberships",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "topic_id",
            sa.Integer,
            sa.ForeignKey("silver.topics.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("silver.users.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="follower"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("topic_id", "user_id", name="uq_topic_memberships_topic_user"),
        schema="silver",
    )
    op.create_index("ix_topic_memberships_topic_id", "topic_memberships", ["topic_id"], schema="silver")
    op.create_index("ix_topic_memberships_user_id", "topic_memberships", ["user_id"], schema="silver")


def downgrade() -> None:
    op.drop_index("ix_topic_memberships_user_id", table_name="topic_memberships", schema="silver")
    op.drop_index("ix_topic_memberships_topic_id", table_name="topic_memberships", schema="silver")
    op.drop_table("topic_memberships", schema="silver")

    op.drop_constraint("ck_topics_scope_owner", "topics", schema="silver", type_="check")
    op.drop_index("uq_topics_owner_slug_private", table_name="topics", schema="silver")
    op.drop_index("uq_topics_slug_global", table_name="topics", schema="silver")
    op.drop_index("ix_topics_slug", table_name="topics", schema="silver")
    op.drop_index("ix_topics_owner_user_id", table_name="topics", schema="silver")
    op.drop_constraint("fk_topics_owner_user_id", "topics", schema="silver", type_="foreignkey")
    op.drop_column("topics", "owner_user_id", schema="silver")
    op.drop_column("topics", "is_global", schema="silver")

    op.create_index("ix_topics_slug", "topics", ["slug"], unique=True, schema="silver")
    op.create_unique_constraint("topics_slug_key", "topics", ["slug"], schema="silver")

    op.drop_index("ix_users_email", table_name="users", schema="silver")
    op.drop_index("ix_users_provider_subject", table_name="users", schema="silver")
    op.drop_table("users", schema="silver")
