from datetime import datetime

from sqlalchemy import SmallInteger, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RawGovukItem(Base):
    __tablename__ = "raw_govuk_items"
    __table_args__ = {"schema": "bronze"}

    id: Mapped[int] = mapped_column(primary_key=True)
    base_path: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    content_id: Mapped[str | None] = mapped_column(String(64), index=True)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    http_status: Mapped[int] = mapped_column(SmallInteger, default=200)
    source_query: Mapped[str | None] = mapped_column(String(256))


class RawParliamentItem(Base):
    __tablename__ = "raw_parliament_items"
    __table_args__ = (
        UniqueConstraint("source_api", "external_id", name="uq_parliament_source_id"),
        {"schema": "bronze"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_api: Mapped[str] = mapped_column(String(64))
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    source_query: Mapped[str | None] = mapped_column(String(256))
