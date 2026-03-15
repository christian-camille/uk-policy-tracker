"""Tests for the local API router endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.models.gold import GraphNode


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
