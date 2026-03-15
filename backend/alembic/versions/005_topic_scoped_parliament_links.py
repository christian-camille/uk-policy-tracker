"""Add topic link tables for Parliament entities.

Revision ID: 005_topic_links
Revises: 004_local_only_root
Create Date: 2026-03-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_topic_links"
down_revision: Union[str, None] = "004_local_only_root"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bill_topics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "bill_id",
            sa.Integer,
            sa.ForeignKey("silver.bills.id"),
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
        "question_topics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "question_id",
            sa.Integer,
            sa.ForeignKey("silver.written_questions.id"),
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
        "division_topics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "division_id",
            sa.Integer,
            sa.ForeignKey("silver.divisions.id"),
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


def downgrade() -> None:
    op.drop_table("division_topics", schema="silver")
    op.drop_table("question_topics", schema="silver")
    op.drop_table("bill_topics", schema="silver")