from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_content_item_organisation_uniqueness"
down_revision: Union[str, None] = "009_association_provenance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _delete_duplicate_content_item_organisation_links() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM silver.content_item_organisations AS older
            USING silver.content_item_organisations AS newer
            WHERE older.ctid < newer.ctid
              AND older.content_item_id = newer.content_item_id
              AND older.organisation_id = newer.organisation_id
            """
        )
    )


def upgrade() -> None:
    _delete_duplicate_content_item_organisation_links()

    op.create_unique_constraint(
        "uq_content_item_organisation",
        "content_item_organisations",
        ["content_item_id", "organisation_id"],
        schema="silver",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_content_item_organisation",
        "content_item_organisations",
        schema="silver",
        type_="unique",
    )