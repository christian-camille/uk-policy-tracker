"""
Shared test fixtures for the gov-tracker backend test suite.

Uses SQLite in-memory for tests that need database access, mocking
out PostgreSQL-specific features. API endpoint tests use FastAPI's
TestClient with dependency injection to override the real DB.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Generator
from datetime import datetime

import pytest
from sqlalchemy import StaticPool, create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db

# ── SQLite ↔ PostgreSQL type adapters ────────────────────────────────
# Register compile-time adapters so JSONB/ARRAY columns compile to TEXT.

from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "TEXT"


# ── Bind/result processors for ARRAY and JSONB on SQLite ─────────────
# SQLite stores TEXT, so we JSON-serialize lists/dicts on bind
# and deserialize on result.

import sqlite3

_orig_adapt = sqlite3.adapters.get((list, sqlite3.PrepareProtocol))


def _adapt_list(val):
    return json.dumps(val)


def _adapt_dict(val):
    return json.dumps(val)


sqlite3.register_adapter(list, _adapt_list)
sqlite3.register_adapter(dict, _adapt_dict)


def _convert_json(val):
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    return json.loads(val)


from app.main import create_app
from app.models.gold import GraphEdge, GraphNode
from app.models.silver import (
    ActivityEvent,
    Bill,
    ContentItem,
    ContentItemOrganisation,
    ContentItemTopic,
    Division,
    Organisation,
    Person,
    Topic,
    WrittenQuestion,
)


# ── Statement rewriting for SQLite compatibility ─────────────────────


def _rewrite_for_sqlite(statement):
    """Rewrite PostgreSQL-specific SQL for SQLite compatibility."""
    # Strip schema prefixes
    for schema in ("bronze.", "silver.", "gold."):
        statement = statement.replace(schema, "")

    # TRUNCATE → DELETE FROM
    if statement.strip().upper().startswith("TRUNCATE"):
        table_name = statement.strip().split()[-2]  # "TRUNCATE tablename CASCADE"
        # Handle both "TRUNCATE table CASCADE" and "TRUNCATE table"
        parts = statement.strip().split()
        table_name = parts[1]
        statement = f"DELETE FROM {table_name}"

    return statement


# ── Sync engine (for service-layer unit tests) ───────────────────────

SYNC_DB_URL = "sqlite://"


@pytest.fixture
def sync_engine():
    """Create a fresh in-memory SQLite engine per test."""
    engine = create_engine(
        SYNC_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        json_serializer=json.dumps,
        json_deserializer=json.loads,
    )

    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def _sqlite_compat(conn, cursor, statement, parameters, context, executemany):
        statement = _rewrite_for_sqlite(statement)
        return statement, parameters

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sync_engine) -> Generator[Session, None, None]:
    """A sync session for each test. Uses savepoints for rollback."""
    session = sessionmaker(bind=sync_engine)()
    yield session
    session.rollback()
    session.close()


# ── Async engine (for FastAPI endpoint tests) ─────────────────────────

ASYNC_DB_URL = "sqlite+aiosqlite://"


@pytest.fixture
async def async_engine():
    """Create a fresh async in-memory SQLite engine per test."""
    engine = create_async_engine(
        ASYNC_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        json_serializer=json.dumps,
        json_deserializer=json.loads,
    )

    @event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
    def _sqlite_compat(conn, cursor, statement, parameters, context, executemany):
        statement = _rewrite_for_sqlite(statement)
        return statement, parameters

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """An async session backed by the in-memory SQLite."""
    async_session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session


@pytest.fixture
def app(async_engine):
    """FastAPI app with DB dependency overridden to use test async engine."""
    test_app = create_app()

    async def _override_get_db():
        async_session_factory = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session_factory() as session:
            yield session

    test_app.dependency_overrides[get_db] = _override_get_db
    return test_app


@pytest.fixture
async def client(app):
    """Async test client for FastAPI endpoint tests."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Factory helpers ──────────────────────────────────────────────────


def make_topic(
    db: Session | AsyncSession,
    *,
    slug: str = "ai-policy",
    label: str = "AI Policy",
    search_queries: list[str] | None = None,
) -> Topic:
    """Create and flush a Topic. Works with sync sessions only."""
    topic = Topic(
        slug=slug,
        label=label,
        search_queries=search_queries or ["artificial intelligence"],
    )
    db.add(topic)
    db.flush()
    return topic


def make_content_item(
    db: Session,
    *,
    content_id: str = "abc-123",
    base_path: str = "/government/test-doc",
    title: str = "Test Document",
    document_type: str = "policy_paper",
    description: str | None = "A test document",
) -> ContentItem:
    """Create and flush a ContentItem."""
    ci = ContentItem(
        content_id=content_id,
        base_path=base_path,
        title=title,
        document_type=document_type,
        description=description,
        govuk_url=f"https://www.gov.uk{base_path}",
    )
    db.add(ci)
    db.flush()
    return ci


def make_person(
    db: Session,
    *,
    parliament_id: int = 1001,
    name_display: str = "Keir Starmer",
    party: str = "Labour",
    house: str = "Commons",
) -> Person:
    """Create and flush a Person."""
    person = Person(
        parliament_id=parliament_id,
        name_display=name_display,
        party=party,
        house=house,
        is_active=True,
    )
    db.add(person)
    db.flush()
    return person


def make_bill(
    db: Session,
    *,
    parliament_bill_id: int = 5001,
    short_title: str = "Online Safety Bill",
    current_house: str = "Commons",
) -> Bill:
    """Create and flush a Bill."""
    bill = Bill(
        parliament_bill_id=parliament_bill_id,
        short_title=short_title,
        current_house=current_house,
        is_act=False,
        is_defeated=False,
    )
    db.add(bill)
    db.flush()
    return bill


def make_organisation(
    db: Session,
    *,
    content_id: str = "org-001",
    title: str = "Department for Science",
    acronym: str | None = "DSIT",
    slug: str = "department-for-science",
) -> Organisation:
    """Create and flush an Organisation."""
    org = Organisation(
        content_id=content_id,
        title=title,
        acronym=acronym,
        slug=slug,
    )
    db.add(org)
    db.flush()
    return org


def make_graph_node(
    db: Session,
    *,
    entity_type: str = "person",
    entity_id: int = 1,
    label: str = "Test Node",
    properties: dict | None = None,
) -> GraphNode:
    """Create and flush a GraphNode."""
    node = GraphNode(
        entity_type=entity_type,
        entity_id=entity_id,
        label=label,
        properties=properties,
    )
    db.add(node)
    db.flush()
    return node
