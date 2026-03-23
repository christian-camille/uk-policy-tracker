"""Add structured keyword rules to topics.

Revision ID: 007_topic_keyword_rules
Revises: 006_question_answers
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_topic_keyword_rules"
down_revision: Union[str, None] = "006_question_answers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "topics",
        sa.Column("keyword_groups", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="silver",
    )
    op.add_column(
        "topics",
        sa.Column("excluded_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="silver",
    )

    op.execute(
        """
        UPDATE silver.topics
        SET keyword_groups = to_jsonb(ARRAY[search_queries]),
            excluded_keywords = '[]'::jsonb
        WHERE keyword_groups IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("topics", "excluded_keywords", schema="silver")
    op.drop_column("topics", "keyword_groups", schema="silver")