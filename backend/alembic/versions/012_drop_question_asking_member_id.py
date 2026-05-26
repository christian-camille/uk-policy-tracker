"""Drop legacy question member parliament foreign key.

Revision ID: 012_drop_question_asking_member_id
Revises: 011_question_asking_person_fk
Create Date: 2026-05-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012_drop_question_asking_member_id"
down_revision: Union[str, None] = "011_question_asking_person_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE silver.written_questions
            DROP CONSTRAINT IF EXISTS written_questions_asking_member_id_fkey
            """
        )
    )
    op.drop_column("written_questions", "asking_member_id", schema="silver")


def downgrade() -> None:
    op.add_column(
        "written_questions",
        sa.Column("asking_member_id", sa.Integer(), nullable=True),
        schema="silver",
    )
    op.execute(
        sa.text(
            """
            UPDATE silver.written_questions
            SET asking_member_id = asking_member_parliament_id
            WHERE asking_member_parliament_id IS NOT NULL
            """
        )
    )
    op.create_foreign_key(
        "written_questions_asking_member_id_fkey",
        "written_questions",
        "persons",
        ["asking_member_id"],
        ["parliament_id"],
        source_schema="silver",
        referent_schema="silver",
    )