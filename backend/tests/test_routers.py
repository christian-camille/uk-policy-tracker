"""Tests for the local API router endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.models.gold import GraphEdge, GraphNode
from app.models.silver import ActivityEvent


async def seed_timeline_events(async_session, topic_id: int) -> list[ActivityEvent]:
    base_date = datetime(2026, 3, 1, 12, 0, 0)
    events = [
        ActivityEvent(
            event_type="govuk_publication",
            event_date=base_date,
            title="Policy paper update",
            summary="Long-term transport strategy",
            source_url="https://www.gov.uk/example-policy-paper",
            source_entity_type="content_item",
            source_entity_id=101,
            topic_id=topic_id,
        ),
        ActivityEvent(
            event_type="question_tabled",
            event_date=base_date + timedelta(days=1),
            title="Written question tabled",
            summary="Parliamentary question about rail fares",
            source_url=None,
            source_entity_type="question",
            source_entity_id=102,
            topic_id=topic_id,
        ),
        ActivityEvent(
            event_type="question_answered",
            event_date=base_date + timedelta(days=2),
            title="Written question answered",
            summary="Ministerial response covering bus franchising",
            source_url=None,
            source_entity_type="question",
            source_entity_id=103,
            topic_id=topic_id,
        ),
        ActivityEvent(
            event_type="division_held",
            event_date=base_date + timedelta(days=3),
            title="Division on transport funding",
            summary="Commons division result",
            source_url=None,
            source_entity_type="division",
            source_entity_id=104,
            topic_id=topic_id,
        ),
        ActivityEvent(
            event_type="bill_stage",
            event_date=base_date + timedelta(days=4),
            title="Bus Services Bill committee stage",
            summary=None,
            source_url=None,
            source_entity_type="bill",
            source_entity_id=105,
            topic_id=topic_id,
        ),
    ]
    async_session.add_all(events)
    await async_session.commit()
    return events


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db"] == "connected"
    assert "freshness" in data
    assert "redis" not in data


@pytest.mark.asyncio
async def test_create_topic(client):
    resp = await client.post(
        "/api/topics",
        json={"label": "AI Policy", "search_queries": ["artificial intelligence"]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == "AI Policy"
    assert data["slug"] == "ai-policy"
    assert data["is_global"] is True
    assert data["new_items_count"] == 0


@pytest.mark.asyncio
async def test_create_topic_duplicate_slug_returns_409(client):
    await client.post(
        "/api/topics",
        json={"label": "AI Policy", "search_queries": ["ai"]},
    )
    resp = await client.post(
        "/api/topics",
        json={"label": "AI Policy", "search_queries": ["ai"]},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_topic_forces_global_scope(client):
    resp = await client.post(
        "/api/topics",
        json={"label": "Local Only", "search_queries": ["local"], "is_global": False},
    )
    assert resp.status_code == 201
    assert resp.json()["is_global"] is True


@pytest.mark.asyncio
async def test_list_topics_empty(client):
    resp = await client.get("/api/topics")
    assert resp.status_code == 200
    assert resp.json()["topics"] == []


@pytest.mark.asyncio
async def test_list_topics_with_items(client):
    await client.post(
        "/api/topics",
        json={"label": "Energy", "search_queries": ["energy policy"]},
    )
    await client.post(
        "/api/topics",
        json={"label": "Health", "search_queries": ["nhs"]},
    )
    resp = await client.get("/api/topics")
    data = resp.json()
    assert len(data["topics"]) == 2
    labels = {topic["label"] for topic in data["topics"]}
    assert labels == {"Energy", "Health"}


@pytest.mark.asyncio
async def test_private_scope_returns_empty(client):
    await client.post(
        "/api/topics",
        json={"label": "Shared One", "search_queries": ["shared"]},
    )
    resp = await client.get("/api/topics?scope=private")
    assert resp.status_code == 200
    assert resp.json()["topics"] == []


@pytest.mark.asyncio
async def test_get_topic_by_id(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Defense", "search_queries": ["defense"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.get(f"/api/topics/{topic_id}")
    assert resp.status_code == 200
    assert resp.json()["label"] == "Defense"


@pytest.mark.asyncio
async def test_get_topic_not_found(client):
    resp = await client.get("/api/topics/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_topic(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "To Delete", "search_queries": ["delete"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/topics/{topic_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/topics/{topic_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_topic_not_found(client):
    resp = await client.delete("/api/topics/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_timeline_empty(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Climate", "search_queries": ["climate"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.get(f"/api/topics/{topic_id}/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic_id"] == topic_id
    assert data["events"] == []
    assert data["total"] == 0
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_timeline_not_found(client):
    resp = await client.get("/api/topics/9999/timeline")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_timeline_filters_by_date_range(client, async_session):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Transport", "search_queries": ["transport"]},
    )
    topic_id = create_resp.json()["id"]
    await seed_timeline_events(async_session, topic_id)

    resp = await client.get(
        f"/api/topics/{topic_id}/timeline?since=2026-03-02&until=2026-03-04"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert [event["event_type"] for event in data["events"]] == [
        "division_held",
        "question_answered",
        "question_tabled",
    ]


@pytest.mark.asyncio
async def test_timeline_filters_by_event_type_and_source(client, async_session):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Transport Source", "search_queries": ["transport"]},
    )
    topic_id = create_resp.json()["id"]
    await seed_timeline_events(async_session, topic_id)

    resp = await client.get(
        f"/api/topics/{topic_id}/timeline"
        "?event_type=question_answered&event_type=division_held&source_entity_type=question"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert [event["event_type"] for event in data["events"]] == ["question_answered"]


@pytest.mark.asyncio
async def test_timeline_filters_by_text_search(client, async_session):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Transport Search", "search_queries": ["transport"]},
    )
    topic_id = create_resp.json()["id"]
    await seed_timeline_events(async_session, topic_id)

    resp = await client.get(f"/api/topics/{topic_id}/timeline?q=bus")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert [event["event_type"] for event in data["events"]] == [
        "bill_stage",
        "question_answered",
    ]


@pytest.mark.asyncio
async def test_timeline_filters_preserve_has_more(client, async_session):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Transport Paging", "search_queries": ["transport"]},
    )
    topic_id = create_resp.json()["id"]
    await seed_timeline_events(async_session, topic_id)

    resp = await client.get(f"/api/topics/{topic_id}/timeline?source_entity_type=question&limit=1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["events"]) == 1
    assert data["has_more"] is True


@pytest.mark.asyncio
async def test_timeline_invalid_since_returns_400(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Transport Invalid Since", "search_queries": ["transport"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.get(f"/api/topics/{topic_id}/timeline?since=not-a-date")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid 'since' datetime format"


@pytest.mark.asyncio
async def test_timeline_invalid_until_returns_400(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Transport Invalid Until", "search_queries": ["transport"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.get(f"/api/topics/{topic_id}/timeline?until=not-a-date")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid 'until' datetime format"


@pytest.mark.asyncio
async def test_timeline_rejects_since_after_until(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Transport Bad Range", "search_queries": ["transport"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/topics/{topic_id}/timeline?since=2026-03-05&until=2026-03-04"
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "'since' must be earlier than or equal to 'until'"


@pytest.mark.asyncio
async def test_refresh_topic_runs_direct_service(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Trade", "search_queries": ["trade"]},
    )
    topic_id = create_resp.json()["id"]

    with patch(
        "app.routers.topics.run_topic_refresh",
        return_value={"events": {"events_created": 2}},
    ) as refresh_mock:
        resp = await client.post(f"/api/topics/{topic_id}/refresh")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["topic_id"] == topic_id
    refresh_mock.assert_called_once_with(topic_id)


@pytest.mark.asyncio
async def test_refresh_topic_not_found(client):
    resp = await client.post("/api/topics/9999/refresh")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_entity_not_found(client):
    resp = await client.get("/api/entities/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_entity_lookup_by_source(client, async_session):
    node = GraphNode(entity_type="content_item", entity_id=112, label="Test Content")
    async_session.add(node)
    await async_session.commit()

    resp = await client.get("/api/entities/by-source/content_item/112")

    assert resp.status_code == 200
    data = resp.json()
    assert data["node"]["id"] == node.id
    assert data["node"]["entity_type"] == "content_item"


@pytest.mark.asyncio
async def test_topic_actors_return_enriched_person_labels(client, async_session):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Energy", "search_queries": ["energy"]},
    )
    topic_id = create_resp.json()["id"]
    other_resp = await client.post(
        "/api/topics",
        json={"label": "Health", "search_queries": ["health"]},
    )
    other_topic_id = other_resp.json()["id"]

    topic_node = GraphNode(entity_type="topic", entity_id=topic_id, label="Energy")
    other_topic_node = GraphNode(entity_type="topic", entity_id=other_topic_id, label="Health")
    question_node = GraphNode(entity_type="question", entity_id=201, label="Question 201")
    other_question_node = GraphNode(entity_type="question", entity_id=202, label="Question 202")
    person_node = GraphNode(
        entity_type="person",
        entity_id=301,
        label="John Smith",
        properties={"party": "Labour", "constituency": "Example Central"},
    )
    other_person_node = GraphNode(
        entity_type="person",
        entity_id=302,
        label="Jane Doe",
        properties={"party": "Green", "constituency": "Other Central"},
    )
    async_session.add_all(
        [
            topic_node,
            other_topic_node,
            question_node,
            other_question_node,
            person_node,
            other_person_node,
        ]
    )
    await async_session.flush()

    async_session.add_all(
        [
            GraphEdge(
                source_node_id=question_node.id,
                target_node_id=topic_node.id,
                edge_type="ABOUT_TOPIC",
            ),
            GraphEdge(
                source_node_id=question_node.id,
                target_node_id=person_node.id,
                edge_type="ASKED_BY",
            ),
            GraphEdge(
                source_node_id=other_question_node.id,
                target_node_id=other_topic_node.id,
                edge_type="ABOUT_TOPIC",
            ),
            GraphEdge(
                source_node_id=other_question_node.id,
                target_node_id=other_person_node.id,
                edge_type="ASKED_BY",
            ),
        ]
    )
    await async_session.commit()

    resp = await client.get(f"/api/topics/{topic_id}/actors")
    other_topic_resp = await client.get(f"/api/topics/{other_topic_id}/actors")

    assert resp.status_code == 200
    assert other_topic_resp.status_code == 200
    data = resp.json()
    other_data = other_topic_resp.json()
    assert len(data) == 1
    assert len(other_data) == 1
    assert data[0]["label"] == "John Smith"
    assert other_data[0]["label"] == "Jane Doe"
