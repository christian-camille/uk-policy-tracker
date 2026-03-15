"""Expand GOV.UK content_id fields to support long path-like identifiers.

Revision ID: 002_govuk_id_len
Revises: 001_initial_schema
Create Date: 2026-03-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_govuk_id_len"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "raw_govuk_items",
        "content_id",
        schema="bronze",
        existing_type=sa.String(length=64),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
    op.alter_column(
        "content_items",
        "content_id",
        schema="silver",
        existing_type=sa.String(length=64),
        type_=sa.String(length=512),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "content_items",
        "content_id",
        schema="silver",
        existing_type=sa.String(length=512),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    op.alter_column(
        "raw_govuk_items",
        "content_id",
        schema="bronze",
        existing_type=sa.String(length=512),
        type_=sa.String(length=64),
        existing_nullable=True,
    )