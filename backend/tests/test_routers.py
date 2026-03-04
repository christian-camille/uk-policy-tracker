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
async def test_topics_require_auth(unauthenticated_client):
    resp = await unauthenticated_client.get("/api/topics")
    assert resp.status_code == 401


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
async def test_create_private_topic_assigns_owner(client):
    resp = await client.post(
        "/api/topics",
        json={
            "label": "Private AI",
            "search_queries": ["private ai"],
            "is_global": False,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_global"] is False
    assert data["owner_user_id"] is not None


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
async def test_list_topics_scope_filters_by_user(client, set_auth_user):
    set_auth_user("user-1", "user1@example.com")
    await client.post(
        "/api/topics",
        json={"label": "Shared One", "search_queries": ["shared"], "is_global": True},
    )
    await client.post(
        "/api/topics",
        json={
            "label": "User1 Private",
            "search_queries": ["u1"],
            "is_global": False,
        },
    )

    set_auth_user("user-2", "user2@example.com")
    await client.post(
        "/api/topics",
        json={
            "label": "User2 Private",
            "search_queries": ["u2"],
            "is_global": False,
        },
    )

    set_auth_user("user-1", "user1@example.com")
    all_topics = (await client.get("/api/topics?scope=all")).json()["topics"]
    all_labels = {topic["label"] for topic in all_topics}
    assert "Shared One" in all_labels
    assert "User1 Private" in all_labels
    assert "User2 Private" not in all_labels

    private_topics = (await client.get("/api/topics?scope=private")).json()["topics"]
    private_labels = {topic["label"] for topic in private_topics}
    assert private_labels == {"User1 Private"}


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
async def test_private_topic_forbidden_to_other_user(client, set_auth_user):
    set_auth_user("owner-user", "owner@example.com")
    create_resp = await client.post(
        "/api/topics",
        json={
            "label": "Owner Private",
            "search_queries": ["owner-only"],
            "is_global": False,
        },
    )
    topic_id = create_resp.json()["id"]

    set_auth_user("other-user", "other@example.com")
    resp = await client.get(f"/api/topics/{topic_id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_topic(client):
    create_resp = await client.post(
        "/api/topics",
        json={
            "label": "To Delete",
            "search_queries": ["delete"],
            "is_global": False,
        },
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
async def test_delete_shared_topic_forbidden(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Shared Topic", "search_queries": ["shared"], "is_global": True},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/topics/{topic_id}")
    assert resp.status_code == 403


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
