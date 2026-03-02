"""Initial schema: bronze, silver, gold layers

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    op.execute("CREATE SCHEMA IF NOT EXISTS silver")
    op.execute("CREATE SCHEMA IF NOT EXISTS gold")

    # Enable pg_trgm for fuzzy matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── Bronze layer ──────────────────────────────────────────────────────

    op.create_table(
        "raw_govuk_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("base_path", sa.String(512), nullable=False, unique=True, index=True),
        sa.Column("content_id", sa.String(64), index=True),
        sa.Column("raw_json", postgresql.JSONB, nullable=False),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("http_status", sa.SmallInteger, default=200),
        sa.Column("source_query", sa.String(256)),
        schema="bronze",
    )

    op.create_table(
        "raw_parliament_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_api", sa.String(64), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False, index=True),
        sa.Column("raw_json", postgresql.JSONB, nullable=False),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("source_query", sa.String(256)),
        sa.UniqueConstraint("source_api", "external_id", name="uq_parliament_source_id"),
        schema="bronze",
    )

    # ── Silver layer ──────────────────────────────────────────────────────

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("label", sa.String(256), nullable=False),
        sa.Column("search_queries", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_refreshed_at", sa.DateTime),
        schema="silver",
    )

    op.create_table(
        "content_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("content_id", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("base_path", sa.String(512), nullable=False, unique=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("document_type", sa.String(128), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("public_updated_at", sa.DateTime),
        sa.Column("first_seen_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("govuk_url", sa.String(512), nullable=False),
        sa.Column(
            "raw_item_id",
            sa.Integer,
            sa.ForeignKey("bronze.raw_govuk_items.id"),
        ),
        schema="silver",
    )

    op.create_table(
        "organisations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("content_id", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("acronym", sa.String(32)),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="live"),
        schema="silver",
    )

    op.create_table(
        "persons",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("parliament_id", sa.Integer, nullable=False, unique=True, index=True),
        sa.Column("name_display", sa.String(256), nullable=False),
        sa.Column("name_list", sa.String(256)),
        sa.Column("party", sa.String(128)),
        sa.Column("house", sa.String(16)),
        sa.Column("constituency", sa.String(256)),
        sa.Column("thumbnail_url", sa.String(512)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        schema="silver",
    )

    # Create trigram index on person names for fuzzy matching
    op.execute(
        "CREATE INDEX ix_persons_name_trgm ON silver.persons "
        "USING gin (name_display gin_trgm_ops)"
    )

    op.create_table(
        "bills",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("parliament_bill_id", sa.Integer, nullable=False, unique=True, index=True),
        sa.Column("short_title", sa.String(512), nullable=False),
        sa.Column("current_house", sa.String(16)),
        sa.Column("originating_house", sa.String(16)),
        sa.Column("last_update", sa.DateTime),
        sa.Column("is_act", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_defeated", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("current_stage", sa.String(128)),
        schema="silver",
    )

    # Trigram index on bill titles for fuzzy matching
    op.execute(
        "CREATE INDEX ix_bills_title_trgm ON silver.bills "
        "USING gin (short_title gin_trgm_ops)"
    )

    op.create_table(
        "written_questions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "parliament_question_id", sa.Integer, nullable=False, unique=True, index=True
        ),
        sa.Column("uin", sa.String(32), nullable=False),
        sa.Column("heading", sa.String(512), nullable=False),
        sa.Column("question_text", sa.Text),
        sa.Column("house", sa.String(16), nullable=False),
        sa.Column("date_tabled", sa.Date),
        sa.Column("date_answered", sa.Date),
        sa.Column(
            "asking_member_id",
            sa.Integer,
            sa.ForeignKey("silver.persons.parliament_id"),
        ),
        sa.Column("answering_body", sa.String(256)),
        schema="silver",
    )

    op.create_table(
        "divisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "parliament_division_id", sa.Integer, nullable=False, unique=True, index=True
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("date", sa.DateTime, nullable=False),
        sa.Column("house", sa.String(16), nullable=False),
        sa.Column("aye_count", sa.Integer, nullable=False),
        sa.Column("no_count", sa.Integer, nullable=False),
        sa.Column("number", sa.Integer),
        schema="silver",
    )

    # ── Silver junction tables ────────────────────────────────────────────

    op.create_table(
        "content_item_topics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "content_item_id",
            sa.Integer,
            sa.ForeignKey("silver.content_items.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "topic_id",
            sa.Integer,
            sa.ForeignKey("silver.topics.id"),
            nullable=False,
            index=True,
        ),
        schema="silver",
    )

    op.create_table(
        "content_item_organisations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "content_item_id",
            sa.Integer,
            sa.ForeignKey("silver.content_items.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organisation_id",
            sa.Integer,
            sa.ForeignKey("silver.organisations.id"),
            nullable=False,
            index=True,
        ),
        schema="silver",
    )

    op.create_table(
        "entity_mentions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "content_item_id",
            sa.Integer,
            sa.ForeignKey("silver.content_items.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("mentioned_entity_type", sa.String(64), nullable=False),
        sa.Column("mentioned_entity_id", sa.Integer, nullable=False),
        sa.Column("mention_text", sa.String(512), nullable=False),
        sa.Column("confidence", sa.Float),
        schema="silver",
    )

    # ── Silver activity events ────────────────────────────────────────────

    op.create_table(
        "activity_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_date", sa.DateTime, nullable=False, index=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("source_url", sa.String(512)),
        sa.Column("source_entity_type", sa.String(64), nullable=False),
        sa.Column("source_entity_id", sa.Integer, nullable=False),
        sa.Column(
            "topic_id",
            sa.Integer,
            sa.ForeignKey("silver.topics.id"),
            index=True,
        ),
        schema="silver",
    )

    # ── Gold layer ────────────────────────────────────────────────────────

    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("label", sa.String(512), nullable=False),
        sa.Column("properties", postgresql.JSONB),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_node_entity"),
        schema="gold",
    )
    op.create_index(
        "ix_node_entity", "graph_nodes", ["entity_type", "entity_id"], schema="gold"
    )

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "source_node_id",
            sa.Integer,
            sa.ForeignKey("gold.graph_nodes.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_node_id",
            sa.Integer,
            sa.ForeignKey("gold.graph_nodes.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("edge_type", sa.String(64), nullable=False),
        sa.Column("properties", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        schema="gold",
    )
    op.create_index(
        "ix_edge_source_type",
        "graph_edges",
        ["source_node_id", "edge_type"],
        schema="gold",
    )
    op.create_index(
        "ix_edge_target_type",
        "graph_edges",
        ["target_node_id", "edge_type"],
        schema="gold",
    )


def downgrade() -> None:
    # Gold
    op.drop_table("graph_edges", schema="gold")
    op.drop_table("graph_nodes", schema="gold")

    # Silver
    op.drop_table("activity_events", schema="silver")
    op.drop_table("entity_mentions", schema="silver")
    op.drop_table("content_item_organisations", schema="silver")
    op.drop_table("content_item_topics", schema="silver")
    op.drop_table("divisions", schema="silver")
    op.drop_table("written_questions", schema="silver")
    op.drop_table("bills", schema="silver")
    op.drop_table("persons", schema="silver")
    op.drop_table("organisations", schema="silver")
    op.drop_table("content_items", schema="silver")
    op.drop_table("topics", schema="silver")

    # Bronze
    op.drop_table("raw_parliament_items", schema="bronze")
    op.drop_table("raw_govuk_items", schema="bronze")

    # Schemas and extensions
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP SCHEMA IF EXISTS gold CASCADE")
    op.execute("DROP SCHEMA IF EXISTS silver CASCADE")
    op.execute("DROP SCHEMA IF EXISTS bronze CASCADE")
