"""Add provenance columns to topic association tables.

Revision ID: 009_association_provenance
Revises: 008_mp_tracking
Create Date: 2026-04-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009_association_provenance"
down_revision: Union[str, None] = "008_mp_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PROVENANCE_COLUMN_DEFS = (
    ("matched_at", sa.DateTime()),
    ("last_matched_at", sa.DateTime()),
    ("match_method", sa.String(length=64)),
    ("matched_by_query", sa.String(length=256)),
    ("matched_by_rule_group", postgresql.JSONB(astext_type=sa.Text())),
    ("refresh_run_id", sa.String(length=64)),
)


def _delete_duplicate_pairs(table_name: str, left_column: str, right_column: str) -> None:
    op.execute(
        sa.text(
            f"""
            DELETE FROM silver.{table_name} AS older
            USING silver.{table_name} AS newer
            WHERE older.ctid < newer.ctid
              AND older.{left_column} = newer.{left_column}
              AND older.{right_column} = newer.{right_column}
            """
        )
    )


def _add_provenance_columns(table_name: str) -> None:
    for column_name, column_type in PROVENANCE_COLUMN_DEFS:
        op.add_column(
            table_name,
            sa.Column(column_name, column_type, nullable=True),
            schema="silver",
        )


def _drop_provenance_columns(table_name: str) -> None:
    for column_name, _ in reversed(PROVENANCE_COLUMN_DEFS):
        op.drop_column(table_name, column_name, schema="silver")


def upgrade() -> None:
    _add_provenance_columns("content_item_topics")
    _add_provenance_columns("bill_topics")
    _add_provenance_columns("question_topics")
    _add_provenance_columns("division_topics")

    _delete_duplicate_pairs("content_item_topics", "content_item_id", "topic_id")
    _delete_duplicate_pairs("bill_topics", "bill_id", "topic_id")
    _delete_duplicate_pairs("question_topics", "question_id", "topic_id")
    _delete_duplicate_pairs("division_topics", "division_id", "topic_id")

    op.create_unique_constraint(
        "uq_content_item_topic",
        "content_item_topics",
        ["content_item_id", "topic_id"],
        schema="silver",
    )
    op.create_unique_constraint(
        "uq_bill_topic",
        "bill_topics",
        ["bill_id", "topic_id"],
        schema="silver",
    )
    op.create_unique_constraint(
        "uq_question_topic",
        "question_topics",
        ["question_id", "topic_id"],
        schema="silver",
    )
    op.create_unique_constraint(
        "uq_division_topic",
        "division_topics",
        ["division_id", "topic_id"],
        schema="silver",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_division_topic",
        "division_topics",
        schema="silver",
        type_="unique",
    )
    op.drop_constraint(
        "uq_question_topic",
        "question_topics",
        schema="silver",
        type_="unique",
    )
    op.drop_constraint(
        "uq_bill_topic",
        "bill_topics",
        schema="silver",
        type_="unique",
    )
    op.drop_constraint(
        "uq_content_item_topic",
        "content_item_topics",
        schema="silver",
        type_="unique",
    )

    _drop_provenance_columns("division_topics")
    _drop_provenance_columns("question_topics")
    _drop_provenance_columns("bill_topics")
    _drop_provenance_columns("content_item_topics")