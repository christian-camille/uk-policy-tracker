"""Tests for the API router endpoints (topics, health, entities)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gold import GraphEdge, GraphNode
from app.models.silver import ActivityEvent, Topic


# ── Health endpoint ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db"] == "connected"
    assert "freshness" in data


# ── Topics CRUD ──────────────────────────────────────────────────────


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
async def test_list_topics_empty(client):
    resp = await client.get("/api/topics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["topics"] == []


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
    labels = {t["label"] for t in data["topics"]}
    assert "Energy" in labels
    assert "Health" in labels


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


# ── Timeline ─────────────────────────────────────────────────────────


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


# ── Refresh ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_topic_returns_202(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Trade", "search_queries": ["trade"]},
    )
    topic_id = create_resp.json()["id"]

    # refresh_single_topic is imported inside the function body,
    # so we patch it at the pipeline module level
    with patch("app.tasks.pipeline.refresh_single_topic") as mock_task:
        mock_task.delay = MagicMock()
        resp = await client.post(f"/api/topics/{topic_id}/refresh")
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_refresh_topic_not_found(client):
    with patch("app.tasks.pipeline.refresh_single_topic") as mock_task:
        mock_task.delay = MagicMock()
        resp = await client.post("/api/topics/9999/refresh")
        assert resp.status_code == 404


# ── Entity detail ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_entity_not_found(client):
    resp = await client.get("/api/entities/9999")
    assert resp.status_code == 404
