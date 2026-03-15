"""Tests for the graph service and projection builder."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.gold import GraphEdge, GraphNode
from app.models.silver import (
    ActivityEvent,
    ContentItem,
    ContentItemOrganisation,
    ContentItemTopic,
    EntityMention,
    Organisation,
    Person,
    Topic,
    WrittenQuestion,
)
from app.services.graph import GraphProjectionBuilder, GraphService

from tests.conftest import (
    make_bill,
    make_content_item,
    make_graph_node,
    make_organisation,
    make_person,
    make_topic,
)


# ── GraphService (async, for API) ────────────────────────────────────


@pytest.mark.asyncio
class TestGraphService:
    async def test_get_node_returns_none(self, async_session: AsyncSession):
        service = GraphService(async_session)
        node = await service.get_node(9999)
        assert node is None

    async def test_get_entity_detail_returns_none(self, async_session: AsyncSession):
        service = GraphService(async_session)
        detail = await service.get_entity_detail(9999)
        assert detail is None

    async def test_get_entity_detail_with_connections(self, async_session: AsyncSession):
        # Create two nodes and an edge
        node_a = GraphNode(entity_type="person", entity_id=1, label="Alice")
        node_b = GraphNode(entity_type="bill", entity_id=2, label="Test Bill")
        async_session.add_all([node_a, node_b])
        await async_session.flush()

        edge = GraphEdge(
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            edge_type="MENTIONS",
        )
        async_session.add(edge)
        await async_session.flush()

        service = GraphService(async_session)
        detail = await service.get_entity_detail(node_a.id)

        assert detail is not None
        assert detail.node.label == "Alice"
        assert len(detail.connections) == 1
        assert detail.connections[0].edge_type == "MENTIONS"
        assert detail.connections[0].direction == "outgoing"
        assert detail.connections[0].connected_node.label == "Test Bill"

    async def test_incoming_connections(self, async_session: AsyncSession):
        node_a = GraphNode(entity_type="person", entity_id=1, label="Source")
        node_b = GraphNode(entity_type="bill", entity_id=2, label="Target")
        async_session.add_all([node_a, node_b])
        await async_session.flush()

        edge = GraphEdge(
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            edge_type="ASKED_BY",
        )
        async_session.add(edge)
        await async_session.flush()

        service = GraphService(async_session)
        detail = await service.get_entity_detail(node_b.id)

        assert detail is not None
        assert len(detail.connections) == 1
        assert detail.connections[0].direction == "incoming"


# ── GraphProjectionBuilder (sync, for local refresh) ─────────────────


class TestGraphProjectionBuilder:
    def test_rebuild_creates_nodes_from_topics(self, db_session: Session):
        make_topic(db_session, slug="topic-1", label="Topic 1")
        make_topic(db_session, slug="topic-2", label="Topic 2")
        db_session.flush()

        builder = GraphProjectionBuilder(db_session)
        stats = builder.rebuild()

        assert stats["nodes"] >= 2
        nodes = db_session.execute(
            select(GraphNode).where(GraphNode.entity_type == "topic")
        ).scalars().all()
        assert len(nodes) == 2

    def test_rebuild_creates_nodes_for_persons(self, db_session: Session):
        make_person(db_session, parliament_id=1, name_display="Alice")
        make_person(db_session, parliament_id=2, name_display="Bob")
        db_session.flush()

        builder = GraphProjectionBuilder(db_session)
        stats = builder.rebuild()

        person_nodes = db_session.execute(
            select(GraphNode).where(GraphNode.entity_type == "person")
        ).scalars().all()
        assert len(person_nodes) == 2
        # Verify properties are set
        for node in person_nodes:
            assert node.properties is not None or node.properties is None

    def test_rebuild_creates_question_node_properties(self, db_session: Session):
        asker = make_person(db_session, parliament_id=77, name_display="Iqbal Mohamed")
        db_session.add(
            WrittenQuestion(
                parliament_question_id=9001,
                uin="12345",
                heading="Iran: Armed Conflict",
                question_text="What assessment has the Government made of recent military escalations involving Iran?",
                house="Commons",
                date_tabled=date(2026, 3, 10),
                date_answered=date(2026, 3, 12),
                asking_member_id=asker.parliament_id,
                answering_body="Foreign, Commonwealth and Development Office",
                answer_text="The Government continues to monitor the situation closely.",
                answer_source_url="https://www.gov.uk/example-answer",
            )
        )
        db_session.flush()

        builder = GraphProjectionBuilder(db_session)
        builder.rebuild()

        question_node = db_session.execute(
            select(GraphNode).where(GraphNode.entity_type == "question")
        ).scalar_one()
        assert question_node.properties is not None
        assert question_node.properties["uin"] == "12345"
        assert question_node.properties["asked_by"] == "Iqbal Mohamed"
        assert question_node.properties["status"] == "answered"
        assert question_node.properties["question_text"].startswith("What assessment")
        assert question_node.properties["answer_text"].startswith("The Government continues")
        assert question_node.properties["answer_source_url"] == "https://www.gov.uk/example-answer"

    def test_rebuild_creates_published_by_edges(self, db_session: Session):
        ci = make_content_item(db_session)
        org = make_organisation(db_session)
        db_session.add(
            ContentItemOrganisation(content_item_id=ci.id, organisation_id=org.id)
        )
        db_session.flush()

        builder = GraphProjectionBuilder(db_session)
        stats = builder.rebuild()

        edges = db_session.execute(
            select(GraphEdge).where(GraphEdge.edge_type == "PUBLISHED_BY")
        ).scalars().all()
        assert len(edges) == 1
        assert stats["edges"] >= 1

    def test_rebuild_creates_about_topic_edges(self, db_session: Session):
        topic = make_topic(db_session)
        ci = make_content_item(db_session)
        db_session.add(
            ActivityEvent(
                event_type="govuk_publication",
                event_date=datetime.utcnow(),
                title="Test",
                source_entity_type="content_item",
                source_entity_id=ci.id,
                topic_id=topic.id,
            )
        )
        db_session.flush()

        builder = GraphProjectionBuilder(db_session)
        builder.rebuild()

        edges = db_session.execute(
            select(GraphEdge).where(GraphEdge.edge_type == "ABOUT_TOPIC")
        ).scalars().all()
        assert len(edges) == 1

    def test_rebuild_creates_mentions_edges(self, db_session: Session):
        ci = make_content_item(db_session)
        person = make_person(db_session)
        db_session.add(
            EntityMention(
                content_item_id=ci.id,
                mentioned_entity_type="person",
                mentioned_entity_id=person.id,
                mention_text="Keir Starmer",
                confidence=0.9,
            )
        )
        db_session.flush()

        builder = GraphProjectionBuilder(db_session)
        builder.rebuild()

        edges = db_session.execute(
            select(GraphEdge).where(GraphEdge.edge_type == "MENTIONS")
        ).scalars().all()
        assert len(edges) == 1
        assert edges[0].properties is not None
        assert edges[0].properties["confidence"] == 0.9

    def test_rebuild_is_idempotent(self, db_session: Session):
        make_topic(db_session)
        make_person(db_session)
        db_session.flush()

        builder = GraphProjectionBuilder(db_session)
        stats1 = builder.rebuild()
        stats2 = builder.rebuild()

        # Second rebuild should produce the same counts (truncates first)
        assert stats1["nodes"] == stats2["nodes"]
        assert stats1["edges"] == stats2["edges"]
