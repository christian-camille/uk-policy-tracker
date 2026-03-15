"""Expand organisation acronym field for long GOV.UK publisher values.

Revision ID: 003_org_acronym
Revises: 002_govuk_id_len
Create Date: 2026-03-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_org_acronym"
down_revision: Union[str, None] = "002_govuk_id_len"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "organisations",
        "acronym",
        schema="silver",
        existing_type=sa.String(length=32),
        type_=sa.String(length=256),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "organisations",
        "acronym",
        schema="silver",
        existing_type=sa.String(length=256),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
