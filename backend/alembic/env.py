import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from alembic.ddl.impl import DefaultImpl
from sqlalchemy import engine_from_config, pool
import sqlalchemy as sa
from sqlalchemy.engine import Connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import Base

config = context.config

# Override sqlalchemy.url from environment if available
database_url = os.environ.get("DATABASE_URL_SYNC")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if (
    config.config_file_name is not None
    and config.get_section("loggers")
    and config.get_section("handlers")
    and config.get_section("formatters")
):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
ALEMBIC_VERSION_NUM_LENGTH = 255


def _version_table_impl(
    self: DefaultImpl,
    *,
    version_table: str,
    version_table_schema: str | None,
    version_table_pk: bool,
    **_: object,
) -> sa.Table:
    return sa.Table(
        version_table,
        sa.MetaData(),
        sa.Column(
            "version_num",
            sa.String(length=ALEMBIC_VERSION_NUM_LENGTH),
            nullable=False,
            primary_key=version_table_pk,
        ),
        schema=version_table_schema,
    )


DefaultImpl.version_table_impl = _version_table_impl


def _ensure_version_table_width(connection: Connection) -> None:
    inspector = sa.inspect(connection)
    if not inspector.has_table("alembic_version", schema="public"):
        return

    version_column = next(
        (
            column
            for column in inspector.get_columns("alembic_version", schema="public")
            if column["name"] == "version_num"
        ),
        None,
    )
    if version_column is None:
        return

    current_length = getattr(version_column["type"], "length", None)
    if current_length is None or current_length >= ALEMBIC_VERSION_NUM_LENGTH:
        return

    connection.execute(
        sa.text(
            "ALTER TABLE public.alembic_version "
            f"ALTER COLUMN version_num TYPE VARCHAR({ALEMBIC_VERSION_NUM_LENGTH})"
        )
    )


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _ensure_version_table_width(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema="public",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
