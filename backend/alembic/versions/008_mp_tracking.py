"""Add MP tracking: is_tracked on persons, division_votes table.

Revision ID: 008_mp_tracking
Revises: 007_topic_keyword_rules
Create Date: 2026-03-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_mp_tracking"
down_revision: Union[str, None] = "007_topic_keyword_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tracking columns to persons
    op.add_column(
        "persons",
        sa.Column("is_tracked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema="silver",
    )
    op.add_column(
        "persons",
        sa.Column("last_refreshed_at", sa.DateTime(), nullable=True),
        schema="silver",
    )

    # Create division_votes table
    op.create_table(
        "division_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("division_id", sa.Integer(), sa.ForeignKey("silver.divisions.id"), nullable=False),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("silver.persons.id"), nullable=False),
        sa.Column("vote", sa.String(16), nullable=False),
        sa.Column("parliament_member_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("division_id", "person_id", name="uq_division_person_vote"),
        schema="silver",
    )
    op.create_index(
        "ix_silver_division_votes_division_id",
        "division_votes",
        ["division_id"],
        schema="silver",
    )
    op.create_index(
        "ix_silver_division_votes_person_id",
        "division_votes",
        ["person_id"],
        schema="silver",
    )


def downgrade() -> None:
    op.drop_index("ix_silver_division_votes_person_id", table_name="division_votes", schema="silver")
    op.drop_index("ix_silver_division_votes_division_id", table_name="division_votes", schema="silver")
    op.drop_table("division_votes", schema="silver")
    op.drop_column("persons", "last_refreshed_at", schema="silver")
    op.drop_column("persons", "is_tracked", schema="silver")
