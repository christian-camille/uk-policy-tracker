"""Add full answer fields to written questions.

Revision ID: 006_question_answers
Revises: 005_topic_links
Create Date: 2026-03-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_question_answers"
down_revision: Union[str, None] = "005_topic_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "written_questions",
        sa.Column("answer_text", sa.Text(), nullable=True),
        schema="silver",
    )
    op.add_column(
        "written_questions",
        sa.Column("answer_source_url", sa.String(length=512), nullable=True),
        schema="silver",
    )


def downgrade() -> None:
    op.drop_column("written_questions", "answer_source_url", schema="silver")
    op.drop_column("written_questions", "answer_text", schema="silver")