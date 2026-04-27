from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    label: Mapped[str] = mapped_column(String(256))
    search_queries: Mapped[list[str]] = mapped_column(ARRAY(String))
    keyword_groups: Mapped[list[list[str]] | None] = mapped_column(JSONB, default=None)
    excluded_keywords: Mapped[list[str] | None] = mapped_column(JSONB, default=None)
    is_global: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_refreshed_at: Mapped[datetime | None] = mapped_column(default=None)


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    base_path: Mapped[str] = mapped_column(String(512), unique=True)
    title: Mapped[str] = mapped_column(String(512))
    document_type: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    public_updated_at: Mapped[datetime | None] = mapped_column(default=None)
    first_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    govuk_url: Mapped[str] = mapped_column(String(512))
    raw_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("bronze.raw_govuk_items.id"), default=None
    )


class Organisation(Base):
    __tablename__ = "organisations"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    acronym: Mapped[str | None] = mapped_column(String(256))
    slug: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(32), default="live")


class Person(Base):
    __tablename__ = "persons"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    parliament_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name_display: Mapped[str] = mapped_column(String(256))
    name_list: Mapped[str | None] = mapped_column(String(256))
    party: Mapped[str | None] = mapped_column(String(128))
    house: Mapped[str | None] = mapped_column(String(16))
    constituency: Mapped[str | None] = mapped_column(String(256))
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    parliament_bill_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    short_title: Mapped[str] = mapped_column(String(512))
    current_house: Mapped[str | None] = mapped_column(String(16))
    originating_house: Mapped[str | None] = mapped_column(String(16))
    last_update: Mapped[datetime | None] = mapped_column(default=None)
    is_act: Mapped[bool] = mapped_column(Boolean, default=False)
    is_defeated: Mapped[bool] = mapped_column(Boolean, default=False)
    current_stage: Mapped[str | None] = mapped_column(String(128))


class WrittenQuestion(Base):
    __tablename__ = "written_questions"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    parliament_question_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    uin: Mapped[str] = mapped_column(String(32))
    heading: Mapped[str] = mapped_column(String(512))
    question_text: Mapped[str | None] = mapped_column(Text)
    house: Mapped[str] = mapped_column(String(16))
    date_tabled: Mapped[date | None] = mapped_column(Date, default=None)
    date_answered: Mapped[date | None] = mapped_column(Date, default=None)
    asking_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("silver.persons.parliament_id"), default=None
    )
    answering_body: Mapped[str | None] = mapped_column(String(256))
    answer_text: Mapped[str | None] = mapped_column(Text)
    answer_source_url: Mapped[str | None] = mapped_column(String(512))


class Division(Base):
    __tablename__ = "divisions"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    parliament_division_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    date: Mapped[datetime] = mapped_column()
    house: Mapped[str] = mapped_column(String(16))
    aye_count: Mapped[int] = mapped_column(Integer)
    no_count: Mapped[int] = mapped_column(Integer)
    number: Mapped[int | None] = mapped_column(Integer, default=None)


class ContentItemTopic(Base):
    """Junction table linking content items to topics they were discovered under."""

    __tablename__ = "content_item_topics"
    __table_args__ = (
        UniqueConstraint("content_item_id", "topic_id", name="uq_content_item_topic"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("silver.content_items.id"), index=True
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("silver.topics.id"), index=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    match_method: Mapped[str | None] = mapped_column(String(64), default=None)
    matched_by_query: Mapped[str | None] = mapped_column(String(256), default=None)
    matched_by_rule_group: Mapped[list[list[str]] | None] = mapped_column(JSONB, default=None)
    refresh_run_id: Mapped[str | None] = mapped_column(String(64), default=None)


class BillTopic(Base):
    """Junction table linking Parliament bills to topics they were discovered under."""

    __tablename__ = "bill_topics"
    __table_args__ = (
        UniqueConstraint("bill_id", "topic_id", name="uq_bill_topic"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("silver.bills.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("silver.topics.id"), index=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    match_method: Mapped[str | None] = mapped_column(String(64), default=None)
    matched_by_query: Mapped[str | None] = mapped_column(String(256), default=None)
    matched_by_rule_group: Mapped[list[list[str]] | None] = mapped_column(JSONB, default=None)
    refresh_run_id: Mapped[str | None] = mapped_column(String(64), default=None)


class QuestionTopic(Base):
    """Junction table linking written questions to topics they were discovered under."""

    __tablename__ = "question_topics"
    __table_args__ = (
        UniqueConstraint("question_id", "topic_id", name="uq_question_topic"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("silver.written_questions.id"), index=True
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("silver.topics.id"), index=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    match_method: Mapped[str | None] = mapped_column(String(64), default=None)
    matched_by_query: Mapped[str | None] = mapped_column(String(256), default=None)
    matched_by_rule_group: Mapped[list[list[str]] | None] = mapped_column(JSONB, default=None)
    refresh_run_id: Mapped[str | None] = mapped_column(String(64), default=None)


class DivisionTopic(Base):
    """Junction table linking divisions to topics they were discovered under."""

    __tablename__ = "division_topics"
    __table_args__ = (
        UniqueConstraint("division_id", "topic_id", name="uq_division_topic"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    division_id: Mapped[int] = mapped_column(
        ForeignKey("silver.divisions.id"), index=True
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("silver.topics.id"), index=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    match_method: Mapped[str | None] = mapped_column(String(64), default=None)
    matched_by_query: Mapped[str | None] = mapped_column(String(256), default=None)
    matched_by_rule_group: Mapped[list[list[str]] | None] = mapped_column(JSONB, default=None)
    refresh_run_id: Mapped[str | None] = mapped_column(String(64), default=None)


class ContentItemOrganisation(Base):
    """Junction table linking content items to their publishing organisations."""

    __tablename__ = "content_item_organisations"
    __table_args__ = (
        UniqueConstraint(
            "content_item_id",
            "organisation_id",
            name="uq_content_item_organisation",
        ),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("silver.content_items.id"), index=True
    )
    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("silver.organisations.id"), index=True
    )


class EntityMention(Base):
    """Records NLP-extracted entity mentions found in GOV.UK content."""

    __tablename__ = "entity_mentions"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("silver.content_items.id"), index=True
    )
    mentioned_entity_type: Mapped[str] = mapped_column(String(64))
    mentioned_entity_id: Mapped[int] = mapped_column(Integer)
    mention_text: Mapped[str] = mapped_column(String(512))
    confidence: Mapped[float | None] = mapped_column(default=None)


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = {"schema": "silver"}

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64))
    event_date: Mapped[datetime] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(512))
    source_entity_type: Mapped[str] = mapped_column(String(64))
    source_entity_id: Mapped[int] = mapped_column(Integer)
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("silver.topics.id"), index=True, default=None
    )


class DivisionVote(Base):
    """Records how an individual MP voted in a division."""

    __tablename__ = "division_votes"
    __table_args__ = (
        UniqueConstraint("division_id", "person_id", name="uq_division_person_vote"),
        {"schema": "silver"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    division_id: Mapped[int] = mapped_column(
        ForeignKey("silver.divisions.id"), index=True
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("silver.persons.id"), index=True
    )
    vote: Mapped[str] = mapped_column(String(16))  # "aye" or "no"
    parliament_member_id: Mapped[int] = mapped_column(Integer)
