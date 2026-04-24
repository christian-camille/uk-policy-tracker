"""Tests for the local API router endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import httpx
import pytest
import respx
from sqlalchemy import select

from app.models.gold import GraphEdge, GraphNode
from app.models.silver import (
    ActivityEvent,
    Bill,
    BillTopic,
    ContentItem,
    ContentItemTopic,
    Division,
    DivisionTopic,
    Person,
    QuestionTopic,
    WrittenQuestion,
)


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
@respx.mock
async def test_search_members_merges_name_and_constituency_results(client, async_session):
    tracked_member = Person(
        parliament_id=101,
        name_display="Alex Leeds",
        party="Labour",
        house="Commons",
        constituency="Leeds Central and Headingley",
        is_tracked=True,
    )
    async_session.add(tracked_member)
    await async_session.commit()

    def search_mock(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if params.get("Name") == "Leeds":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "value": {
                                "id": 101,
                                "nameDisplayAs": "Alex Leeds",
                                "latestParty": {"name": "Labour"},
                                "latestHouseMembership": {
                                    "house": 1,
                                    "membershipFrom": "Leeds Central and Headingley",
                                    "membershipStatus": {"statusIsActive": True},
                                },
                            }
                        }
                    ],
                    "totalResults": 1,
                },
            )

        if params.get("Location") == "Leeds":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "value": {
                                "id": 101,
                                "nameDisplayAs": "Alex Leeds",
                                "latestParty": {"name": "Labour"},
                                "latestHouseMembership": {
                                    "house": 1,
                                    "membershipFrom": "Leeds Central and Headingley",
                                    "membershipStatus": {"statusIsActive": True},
                                },
                            }
                        },
                        {
                            "value": {
                                "id": 202,
                                "nameDisplayAs": "Rachel Reeves",
                                "latestParty": {"name": "Labour"},
                                "latestHouseMembership": {
                                    "house": 1,
                                    "membershipFrom": "Leeds West and Pudsey",
                                    "membershipStatus": {"statusIsActive": True},
                                },
                            }
                        },
                    ],
                    "totalResults": 2,
                },
            )

        raise AssertionError(f"Unexpected search params: {dict(params.multi_items())}")

    route = respx.get("https://members-api.parliament.uk/api/Members/Search").mock(
        side_effect=search_mock
    )

    resp = await client.get("/api/members/search", params={"name": "Leeds"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert [member["parliament_id"] for member in data["results"]] == [101, 202]
    assert data["results"][0]["is_tracked"] is True
    assert data["results"][0]["match_types"] == ["location", "name"]
    assert data["results"][1]["match_types"] == ["location"]
    assert data["results"][1]["constituency"] == "Leeds West and Pudsey"
    assert route.called
    assert len(route.calls) == 2


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
    assert data["keyword_groups"] == [["artificial intelligence"]]
    assert data["excluded_keywords"] == []
    assert data["is_global"] is True
    assert data["new_items_count"] == 0


@pytest.mark.asyncio
async def test_create_topic_with_keyword_groups_and_exclusions(client):
    resp = await client.post(
        "/api/topics",
        json={
            "label": "Planning Reform",
            "keyword_groups": [["housing", "planning"], ["reform"]],
            "excluded_keywords": ["consultation"],
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["search_queries"] == ["housing", "planning", "reform"]
    assert data["keyword_groups"] == [["housing", "planning"], ["reform"]]
    assert data["excluded_keywords"] == ["consultation"]


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
async def test_update_topic_label_and_queries(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Housing", "search_queries": ["housing"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/topics/{topic_id}",
        json={"label": "Housing Reform", "search_queries": ["housing", "planning reform"]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "Housing Reform"
    assert data["slug"] == "housing-reform"
    assert data["search_queries"] == ["housing", "planning reform"]
    assert data["keyword_groups"] == [["housing", "planning reform"]]


@pytest.mark.asyncio
async def test_update_topic_keyword_groups_and_exclusions(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Housing", "search_queries": ["housing"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/topics/{topic_id}",
        json={
            "keyword_groups": [["housing", "planning"], ["reform"]],
            "excluded_keywords": ["consultation"],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["search_queries"] == ["housing", "planning", "reform"]
    assert data["keyword_groups"] == [["housing", "planning"], ["reform"]]
    assert data["excluded_keywords"] == ["consultation"]


@pytest.mark.asyncio
async def test_update_topic_duplicate_slug_returns_409(client):
    await client.post(
        "/api/topics",
        json={"label": "Original Topic", "search_queries": ["one"]},
    )
    second_resp = await client.post(
        "/api/topics",
        json={"label": "Different Topic", "search_queries": ["two"]},
    )
    second_id = second_resp.json()["id"]

    resp = await client.patch(
        f"/api/topics/{second_id}",
        json={"label": "Original Topic"},
    )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_topic_rejects_empty_queries(client):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Healthcare", "search_queries": ["healthcare"]},
    )
    topic_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/topics/{topic_id}",
        json={"search_queries": ["   ", ""]},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Topic search queries cannot be empty"


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
async def test_delete_topic_removes_topic_links_and_events(client, async_session):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Transport Links", "search_queries": ["transport"]},
    )
    topic_id = create_resp.json()["id"]

    content_item = ContentItem(
        content_id="govuk-transport-1",
        base_path="/government/publications/transport-1",
        title="Transport policy paper",
        document_type="policy_paper",
        govuk_url="https://www.gov.uk/government/publications/transport-1",
    )
    async_session.add(content_item)
    await async_session.flush()

    async_session.add(
        ContentItemTopic(
            content_item_id=content_item.id,
            topic_id=topic_id,
            match_method="search_query",
            matched_by_query="transport",
        )
    )
    async_session.add(
        ActivityEvent(
            event_type="govuk_publication",
            event_date=datetime(2026, 3, 1, 12, 0, 0),
            title="Transport update",
            summary=None,
            source_url="https://www.gov.uk/government/publications/transport-1",
            source_entity_type="content_item",
            source_entity_id=content_item.id,
            topic_id=topic_id,
        )
    )
    await async_session.commit()

    resp = await client.delete(f"/api/topics/{topic_id}")

    assert resp.status_code == 204

    remaining_links = await async_session.execute(
        select(ContentItemTopic).where(ContentItemTopic.topic_id == topic_id)
    )
    remaining_events = await async_session.execute(
        select(ActivityEvent).where(ActivityEvent.topic_id == topic_id)
    )

    assert remaining_links.scalars().all() == []
    assert remaining_events.scalars().all() == []


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
async def test_timeline_includes_written_question_details(client, async_session):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Middle East", "search_queries": ["iran"]},
    )
    topic_id = create_resp.json()["id"]

    async_session.add(
        Person(
            parliament_id=77,
            name_display="Iqbal Mohamed",
            is_active=True,
        )
    )
    await async_session.flush()

    question = WrittenQuestion(
        parliament_question_id=501,
        uin="12345",
        heading="Iran: Armed Conflict",
        question_text="What assessment has the Government made of recent military escalations involving Iran?",
        house="Commons",
        date_tabled=datetime(2026, 3, 10).date(),
        date_answered=datetime(2026, 3, 12).date(),
        asking_member_id=77,
        answering_body="Foreign, Commonwealth and Development Office",
        answer_text="The Government continues to monitor the situation closely.",
        answer_source_url="https://www.gov.uk/example-answer",
    )
    async_session.add(question)
    await async_session.flush()

    async_session.add(
        ActivityEvent(
            event_type="question_answered",
            event_date=datetime(2026, 3, 12, 12, 0, 0),
            title=question.heading,
            summary=question.answering_body,
            source_url=None,
            source_entity_type="question",
            source_entity_id=question.id,
            topic_id=topic_id,
        )
    )
    await async_session.commit()

    resp = await client.get(f"/api/topics/{topic_id}/timeline")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    event = data["events"][0]
    assert event["question_uin"] == "12345"
    assert event["question_house"] == "Commons"
    assert event["asking_member_name"] == "Iqbal Mohamed"
    assert event["question_text"].startswith("What assessment has the Government made")
    assert event["question_date_tabled"] == "2026-03-10"
    assert event["question_date_answered"] == "2026-03-12"
    assert event["question_answer_text"].startswith("The Government continues")
    assert event["question_answer_source_url"] == "https://www.gov.uk/example-answer"
    assert event["question_official_url"] == "https://questions-statements.parliament.uk/written-questions/detail/2026-03-10/12345"


@pytest.mark.asyncio
async def test_timeline_includes_match_provenance(client, async_session):
    create_resp = await client.post(
        "/api/topics",
        json={"label": "Provenance Topic", "search_queries": ["ai"]},
    )
    topic_id = create_resp.json()["id"]

    content_item = ContentItem(
        content_id="doc-1",
        base_path="/government/doc-1",
        title="Policy paper update",
        document_type="policy_paper",
        description="AI strategy",
        govuk_url="https://www.gov.uk/government/doc-1",
    )
    bill = Bill(
        parliament_bill_id=900,
        short_title="AI Regulation Bill",
        current_house="Commons",
        is_act=False,
        is_defeated=False,
    )
    question = WrittenQuestion(
        parliament_question_id=901,
        uin="901",
        heading="AI procurement",
        house="Commons",
    )
    division = Division(
        parliament_division_id=902,
        title="AI funding division",
        date=datetime(2026, 4, 10, 12, 0, 0),
        house="Commons",
        aye_count=100,
        no_count=50,
    )
    async_session.add_all([content_item, bill, question, division])
    await async_session.flush()

    async_session.add_all(
        [
            ContentItemTopic(
                content_item_id=content_item.id,
                topic_id=topic_id,
                matched_at=datetime(2026, 4, 10, 9, 0, 0),
                last_matched_at=datetime(2026, 4, 10, 9, 30, 0),
                match_method="govuk_search",
                matched_by_query="ai",
                matched_by_rule_group=[["ai"]],
                refresh_run_id="refresh-abc",
            ),
            BillTopic(
                bill_id=bill.id,
                topic_id=topic_id,
                matched_at=datetime(2026, 4, 10, 10, 0, 0),
                last_matched_at=datetime(2026, 4, 10, 10, 15, 0),
                match_method="parliament_search",
                matched_by_query="artificial intelligence",
                matched_by_rule_group=[["artificial intelligence"]],
                refresh_run_id="refresh-abc",
            ),
            QuestionTopic(
                question_id=question.id,
                topic_id=topic_id,
                matched_at=datetime(2026, 4, 10, 11, 0, 0),
                last_matched_at=datetime(2026, 4, 10, 11, 5, 0),
                match_method="parliament_search",
                matched_by_query="ai procurement",
                matched_by_rule_group=[["ai", "procurement"]],
                refresh_run_id="refresh-abc",
            ),
            DivisionTopic(
                division_id=division.id,
                topic_id=topic_id,
                matched_at=datetime(2026, 4, 10, 12, 0, 0),
                last_matched_at=datetime(2026, 4, 10, 12, 5, 0),
                match_method="parliament_search",
                matched_by_query="ai funding",
                matched_by_rule_group=[["ai", "funding"]],
                refresh_run_id="refresh-abc",
            ),
            ActivityEvent(
                event_type="govuk_publication",
                event_date=datetime(2026, 4, 10, 13, 0, 0),
                title=content_item.title,
                summary=content_item.description,
                source_url=content_item.govuk_url,
                source_entity_type="content_item",
                source_entity_id=content_item.id,
                topic_id=topic_id,
            ),
            ActivityEvent(
                event_type="bill_stage",
                event_date=datetime(2026, 4, 10, 13, 5, 0),
                title=bill.short_title,
                summary=None,
                source_url=None,
                source_entity_type="bill",
                source_entity_id=bill.id,
                topic_id=topic_id,
            ),
            ActivityEvent(
                event_type="question_tabled",
                event_date=datetime(2026, 4, 10, 13, 10, 0),
                title=question.heading,
                summary=None,
                source_url=None,
                source_entity_type="question",
                source_entity_id=question.id,
                topic_id=topic_id,
            ),
            ActivityEvent(
                event_type="division_held",
                event_date=datetime(2026, 4, 10, 13, 15, 0),
                title=division.title,
                summary=None,
                source_url=None,
                source_entity_type="division",
                source_entity_id=division.id,
                topic_id=topic_id,
            ),
        ]
    )
    await async_session.commit()

    resp = await client.get(f"/api/topics/{topic_id}/timeline")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    methods = {
        event["source_entity_type"]: event["match_provenance"]["match_method"]
        for event in data["events"]
    }
    assert methods == {
        "content_item": "govuk_search",
        "bill": "parliament_search",
        "question": "parliament_search",
        "division": "parliament_search",
    }
    content_item_event = next(
        event for event in data["events"] if event["source_entity_type"] == "content_item"
    )
    assert content_item_event["match_provenance"]["matched_by_query"] == "ai"
    assert content_item_event["match_provenance"]["matched_by_rule_group"] == [["ai"]]
    assert content_item_event["match_provenance"]["refresh_run_id"] == "refresh-abc"


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
async def test_refresh_all_topics_runs_direct_service(client):
    await client.post(
        "/api/topics",
        json={"label": "Transport", "search_queries": ["transport"]},
    )
    await client.post(
        "/api/topics",
        json={"label": "Health", "search_queries": ["health"]},
    )

    mock_result = {
        "status": "completed",
        "topics": 2,
        "results": [
            {"topic_id": 1, "result": {"events": {"events_created": 2}}},
            {"topic_id": 2, "result": {"events": {"events_created": 1}}},
        ],
    }

    with patch(
        "app.routers.topics.run_all_topic_refreshes",
        return_value=mock_result,
    ) as refresh_mock:
        resp = await client.post("/api/topics/refresh-all")

    assert resp.status_code == 200
    assert resp.json() == mock_result
    refresh_mock.assert_called_once_with()


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
async def test_entity_detail_includes_connection_properties(client, async_session):
    person_node = GraphNode(
        entity_type="person",
        entity_id=301,
        label="Ben Obese-Jecty",
        properties={"party": "Conservative", "house": "Commons"},
    )
    question_node = GraphNode(
        entity_type="question",
        entity_id=201,
        label="Iran: Armed Conflict",
        properties={"answering_body": "Ministry of Defence"},
    )
    async_session.add_all([person_node, question_node])
    await async_session.flush()

    async_session.add(
        GraphEdge(
            source_node_id=question_node.id,
            target_node_id=person_node.id,
            edge_type="ASKED_BY",
            properties={
                "question_uin": "118059",
                "status": "answered",
                "date_answered": "2026-03-13",
            },
        )
    )
    await async_session.commit()

    resp = await client.get(f"/api/entities/{person_node.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["connections"]) == 1
    assert data["connections"][0]["properties"]["question_uin"] == "118059"
    assert data["connections"][0]["properties"]["status"] == "answered"


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
