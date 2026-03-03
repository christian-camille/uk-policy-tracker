"""Tests for the slugify helper and Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from app.routers.topics import _slugify
from app.schemas.entities import EdgeResponse, EntityDetailResponse, NodeResponse
from app.schemas.timeline import TimelineEvent, TimelineResponse
from app.schemas.topics import TopicCreate, TopicListResponse, TopicSummary


class TestSlugify:
    def test_basic(self):
        assert _slugify("AI Policy") == "ai-policy"

    def test_special_characters(self):
        assert _slugify("Energy & Climate") == "energy-climate"

    def test_multiple_spaces(self):
        assert _slugify("  Many   Spaces  ") == "many-spaces"

    def test_dashes(self):
        assert _slugify("already-slugified") == "already-slugified"

    def test_mixed(self):
        assert _slugify("UK's NATO Policy!") == "uks-nato-policy"

    def test_trailing_dashes(self):
        assert _slugify("-leading-and-trailing-") == "leading-and-trailing"


class TestTopicSchemas:
    def test_topic_create(self):
        tc = TopicCreate(label="AI Policy", search_queries=["ai", "machine learning"])
        assert tc.label == "AI Policy"
        assert len(tc.search_queries) == 2

    def test_topic_summary_defaults(self):
        ts = TopicSummary(
            id=1,
            slug="ai-policy",
            label="AI Policy",
            search_queries=["ai"],
            last_refreshed_at=None,
        )
        assert ts.new_items_count == 0

    def test_topic_list_response(self):
        ts = TopicSummary(
            id=1, slug="test", label="Test", search_queries=["t"], last_refreshed_at=None
        )
        tlr = TopicListResponse(topics=[ts])
        assert len(tlr.topics) == 1


class TestTimelineSchemas:
    def test_timeline_event(self):
        te = TimelineEvent(
            id=1,
            event_type="govuk_publication",
            event_date=datetime(2024, 1, 15),
            title="Test Event",
            summary="Summary",
            source_url="https://example.com",
            source_entity_type="content_item",
            source_entity_id=10,
        )
        assert te.event_type == "govuk_publication"

    def test_timeline_response(self):
        tr = TimelineResponse(topic_id=1, events=[], total=0, has_more=False)
        assert tr.topic_id == 1
        assert tr.has_more is False


class TestEntitySchemas:
    def test_node_response(self):
        nr = NodeResponse(
            id=1, entity_type="person", entity_id=100, label="Alice", properties=None
        )
        assert nr.entity_type == "person"

    def test_edge_response(self):
        node = NodeResponse(
            id=2, entity_type="bill", entity_id=200, label="Bill A", properties=None
        )
        er = EdgeResponse(edge_type="MENTIONS", direction="outgoing", connected_node=node)
        assert er.edge_type == "MENTIONS"
        assert er.direction == "outgoing"

    def test_entity_detail_response(self):
        node = NodeResponse(
            id=1, entity_type="person", entity_id=100, label="Alice", properties=None
        )
        detail = EntityDetailResponse(node=node, connections=[])
        assert detail.node.label == "Alice"
        assert len(detail.connections) == 0
