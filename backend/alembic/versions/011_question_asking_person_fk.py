"""Add internal person linkage for written questions.

Revision ID: 011_question_asking_person_fk
Revises: 010_content_item_organisation_uniqueness
Create Date: 2026-05-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_question_asking_person_fk"
down_revision: Union[str, None] = "010_content_item_organisation_uniqueness"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "written_questions",
        sa.Column("asking_person_id", sa.Integer(), nullable=True),
        schema="silver",
    )
    op.add_column(
        "written_questions",
        sa.Column("asking_member_parliament_id", sa.Integer(), nullable=True),
        schema="silver",
    )

    op.execute(
        sa.text(
            """
            UPDATE silver.written_questions
            SET asking_member_parliament_id = asking_member_id
            WHERE asking_member_id IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE silver.written_questions AS written_questions
            SET asking_person_id = persons.id
            FROM silver.persons AS persons
            WHERE written_questions.asking_member_id = persons.parliament_id
            """
        )
    )

    op.create_foreign_key(
        "fk_written_questions_asking_person_id",
        "written_questions",
        "persons",
        ["asking_person_id"],
        ["id"],
        source_schema="silver",
        referent_schema="silver",
    )
    op.create_index(
        "ix_written_questions_asking_person_id",
        "written_questions",
        ["asking_person_id"],
        unique=False,
        schema="silver",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_written_questions_asking_person_id",
        table_name="written_questions",
        schema="silver",
    )
    op.drop_constraint(
        "fk_written_questions_asking_person_id",
        "written_questions",
        schema="silver",
        type_="foreignkey",
    )
    op.drop_column("written_questions", "asking_member_parliament_id", schema="silver")
    op.drop_column("written_questions", "asking_person_id", schema="silver")
