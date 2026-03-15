"""Tests for GOV.UK and Parliament API clients."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from app.services.govuk import GovUkClient, GovUkClientSync
from app.services.parliament import ParliamentClient, ParliamentClientSync


# ── GOV.UK Client (async) ────────────────────────────────────────────


@pytest.mark.asyncio
class TestGovUkClient:
    @respx.mock
    async def test_search_sends_correct_params(self):
        route = respx.get("https://www.gov.uk/api/search.json").mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"_id": "/doc/1", "title": "Test"}], "total": 1},
            )
        )
        async with httpx.AsyncClient() as http:
            client = GovUkClient(http)
            result = await client.search("climate change", count=10, start=0)

        assert route.called
        assert result["total"] == 1
        assert len(result["results"]) == 1

        # Verify query params
        request = route.calls.last.request
        assert "q=climate+change" in str(request.url) or "q=climate%20change" in str(request.url)

    @respx.mock
    async def test_search_with_order(self):
        route = respx.get("https://www.gov.uk/api/search.json").mock(
            return_value=httpx.Response(200, json={"results": [], "total": 0})
        )
        async with httpx.AsyncClient() as http:
            client = GovUkClient(http)
            await client.search("energy", order="-public_timestamp")

        request = route.calls.last.request
        assert "order=" in str(request.url)

    @respx.mock
    async def test_get_content(self):
        respx.get("https://www.gov.uk/api/content/government/test-doc").mock(
            return_value=httpx.Response(
                200, json={"base_path": "/government/test-doc", "title": "Test"}
            )
        )
        async with httpx.AsyncClient() as http:
            client = GovUkClient(http)
            result = await client.get_content("/government/test-doc")

        assert result["title"] == "Test"

    @respx.mock
    async def test_discover_for_topic_deduplicates(self):
        respx.get("https://www.gov.uk/api/search.json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"_id": "/doc/1", "title": "Doc 1"},
                        {"_id": "/doc/2", "title": "Doc 2"},
                        {"_id": "/doc/1", "title": "Doc 1 Dup"},
                    ],
                    "total": 3,
                },
            )
        )
        topic = MagicMock()
        topic.slug = "climate"
        topic.search_queries = ["climate change"]

        async with httpx.AsyncClient() as http:
            client = GovUkClient(http)
            results = await client.discover_for_topic(topic)

        # Should deduplicate by _id
        assert len(results) == 2
        ids = {r["_id"] for r in results}
        assert ids == {"/doc/1", "/doc/2"}

    @respx.mock
    async def test_discover_handles_http_error(self):
        respx.get("https://www.gov.uk/api/search.json").mock(
            return_value=httpx.Response(500)
        )
        topic = MagicMock()
        topic.slug = "test"
        topic.search_queries = ["test query"]

        async with httpx.AsyncClient() as http:
            client = GovUkClient(http)
            results = await client.discover_for_topic(topic)

        assert results == []

    @respx.mock
    async def test_discover_handles_transport_error(self):
        respx.get("https://www.gov.uk/api/search.json").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )
        topic = MagicMock()
        topic.slug = "test"
        topic.search_queries = ["test query"]

        async with httpx.AsyncClient() as http:
            client = GovUkClient(http)
            results = await client.discover_for_topic(topic)

        assert results == []


# ── GOV.UK Client (sync) ─────────────────────────────────────────────


class TestGovUkClientSync:
    @respx.mock
    def test_search(self):
        respx.get("https://www.gov.uk/api/search.json").mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"_id": "/doc/1"}], "total": 1},
            )
        )
        with httpx.Client() as http:
            client = GovUkClientSync(http)
            result = client.search("energy policy")

        assert result["total"] == 1

    @respx.mock
    def test_get_content(self):
        respx.get("https://www.gov.uk/api/content/government/doc").mock(
            return_value=httpx.Response(200, json={"title": "Energy"})
        )
        with httpx.Client() as http:
            client = GovUkClientSync(http)
            result = client.get_content("/government/doc")

        assert result["title"] == "Energy"

    @respx.mock
    def test_discover_handles_transport_error(self):
        respx.get("https://www.gov.uk/api/search.json").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )
        topic = MagicMock()
        topic.slug = "test"
        topic.search_queries = ["test query"]

        with httpx.Client() as http:
            client = GovUkClientSync(http)
            results = client.discover_for_topic(topic)

        assert results == []


# ── Parliament Client (async) ────────────────────────────────────────


@pytest.mark.asyncio
class TestParliamentClient:
    @respx.mock
    async def test_search_bills(self):
        respx.get("https://bills-api.parliament.uk/api/v1/Bills").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"billId": 100, "shortTitle": "Test Bill"}]},
            )
        )
        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            result = await client.search_bills("test")

        assert len(result["items"]) == 1
        assert result["items"][0]["billId"] == 100

    @respx.mock
    async def test_search_members(self):
        respx.get("https://members-api.parliament.uk/api/Members/Search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "value": {
                                "id": 999,
                                "nameDisplayAs": "John Smith",
                            }
                        }
                    ]
                },
            )
        )
        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            result = await client.search_members(name="John Smith")

        assert len(result["items"]) == 1

    @respx.mock
    async def test_get_member(self):
        respx.get("https://members-api.parliament.uk/api/Members/999").mock(
            return_value=httpx.Response(
                200,
                json={
                    "value": {
                        "id": 999,
                        "nameDisplayAs": "John Smith",
                        "latestParty": {"name": "Labour"},
                    }
                },
            )
        )
        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            result = await client.get_member(999)

        assert result["id"] == 999
        assert result["nameDisplayAs"] == "John Smith"

    @respx.mock
    async def test_search_questions(self):
        respx.get(
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"value": {"id": 50, "heading": "Energy costs"}}
                    ]
                },
            )
        )
        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            result = await client.search_questions("energy")

        assert len(result["results"]) == 1

    @respx.mock
    async def test_search_divisions(self):
        respx.get(
            "https://commonsvotes-api.parliament.uk/data/divisions.json/search"
        ).mock(
            return_value=httpx.Response(
                200, json=[{"DivisionId": 1, "Title": "Test Division"}]
            )
        )
        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            result = await client.search_divisions("test")

        assert isinstance(result, list)
        assert result[0]["DivisionId"] == 1

    @respx.mock
    async def test_discover_for_topic_all_apis(self):
        respx.get("https://bills-api.parliament.uk/api/v1/Bills").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"billId": 10, "shortTitle": "Bill A"}]},
            )
        )
        respx.get(
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions"
        ).mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"value": {"id": 20, "heading": "Q1"}}]},
            )
        )
        respx.get(
            "https://commonsvotes-api.parliament.uk/data/divisions.json/search"
        ).mock(
            return_value=httpx.Response(
                200, json=[{"DivisionId": 30, "Title": "Div A"}]
            )
        )

        topic = MagicMock()
        topic.slug = "energy"
        topic.search_queries = ["energy"]

        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            results = await client.discover_for_topic(topic)

        assert len(results["bills"]) == 1
        assert len(results["questions"]) == 1
        assert len(results["divisions"]) == 1
        assert results["members"] == []  # Members not directly discovered

    @respx.mock
    async def test_discover_deduplicates_across_queries(self):
        # Same bill returned for two different search queries
        respx.get("https://bills-api.parliament.uk/api/v1/Bills").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"billId": 10, "shortTitle": "Bill A"}]},
            )
        )
        respx.get(
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions"
        ).mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        respx.get(
            "https://commonsvotes-api.parliament.uk/data/divisions.json/search"
        ).mock(return_value=httpx.Response(200, json=[]))

        topic = MagicMock()
        topic.slug = "energy"
        topic.search_queries = ["energy", "power"]

        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            results = await client.discover_for_topic(topic)

        # Bill with billId=10 should appear only once despite two queries
        assert len(results["bills"]) == 1

    @respx.mock
    async def test_discover_continues_after_transport_error(self):
        respx.get("https://bills-api.parliament.uk/api/v1/Bills").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"billId": 10, "shortTitle": "Bill A"}]},
            )
        )
        respx.get(
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions"
        ).mock(side_effect=httpx.ReadTimeout("timed out"))
        respx.get(
            "https://commonsvotes-api.parliament.uk/data/divisions.json/search"
        ).mock(
            return_value=httpx.Response(
                200, json=[{"DivisionId": 30, "Title": "Div A"}]
            )
        )

        topic = MagicMock()
        topic.slug = "energy"
        topic.search_queries = ["energy"]

        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            results = await client.discover_for_topic(topic)

        assert len(results["bills"]) == 1
        assert results["questions"] == []
        assert len(results["divisions"]) == 1

    @respx.mock
    async def test_discover_fetches_members_from_question_ids(self):
        respx.get("https://bills-api.parliament.uk/api/v1/Bills").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        respx.get(
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"value": {"id": 20, "heading": "Q1", "askingMemberId": 999}},
                        {"value": {"id": 21, "heading": "Q2", "askingMemberId": 999}},
                    ]
                },
            )
        )
        respx.get(
            "https://commonsvotes-api.parliament.uk/data/divisions.json/search"
        ).mock(return_value=httpx.Response(200, json=[]))
        member_route = respx.get("https://members-api.parliament.uk/api/Members/999").mock(
            return_value=httpx.Response(
                200,
                json={
                    "value": {
                        "id": 999,
                        "nameDisplayAs": "John Smith",
                        "nameListAs": "Smith, John",
                    }
                },
            )
        )

        topic = MagicMock()
        topic.slug = "energy"
        topic.search_queries = ["energy"]

        async with httpx.AsyncClient() as http:
            client = ParliamentClient(http)
            results = await client.discover_for_topic(topic)

        assert len(results["questions"]) == 2
        assert len(results["members"]) == 1
        assert results["members"][0]["nameDisplayAs"] == "John Smith"
        assert member_route.called


# ── Parliament Client (sync) ─────────────────────────────────────────


class TestParliamentClientSync:
    @respx.mock
    def test_search_bills(self):
        respx.get("https://bills-api.parliament.uk/api/v1/Bills").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"billId": 1}]},
            )
        )
        with httpx.Client() as http:
            client = ParliamentClientSync(http)
            result = client.search_bills("test")

        assert len(result["items"]) == 1

    @respx.mock
    def test_get_member(self):
        respx.get("https://members-api.parliament.uk/api/Members/999").mock(
            return_value=httpx.Response(
                200,
                json={"value": {"id": 999, "nameDisplayAs": "John Smith"}},
            )
        )
        with httpx.Client() as http:
            client = ParliamentClientSync(http)
            result = client.get_member(999)

        assert result["id"] == 999
        assert result["nameDisplayAs"] == "John Smith"

    @respx.mock
    def test_discover_continues_after_transport_error(self):
        respx.get("https://bills-api.parliament.uk/api/v1/Bills").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"billId": 1, "shortTitle": "Bill A"}]},
            )
        )
        respx.get(
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions"
        ).mock(side_effect=httpx.ReadTimeout("timed out"))
        respx.get(
            "https://commonsvotes-api.parliament.uk/data/divisions.json/search"
        ).mock(return_value=httpx.Response(200, json=[]))

        topic = MagicMock()
        topic.slug = "energy"
        topic.search_queries = ["energy"]

        with httpx.Client() as http:
            client = ParliamentClientSync(http)
            results = client.discover_for_topic(topic)

        assert len(results["bills"]) == 1
        assert results["questions"] == []

    @respx.mock
    def test_discover_fetches_members_from_question_ids(self):
        respx.get("https://bills-api.parliament.uk/api/v1/Bills").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        respx.get(
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"value": {"id": 20, "heading": "Q1", "askingMemberId": 999}}
                    ]
                },
            )
        )
        respx.get(
            "https://commonsvotes-api.parliament.uk/data/divisions.json/search"
        ).mock(return_value=httpx.Response(200, json=[]))
        respx.get("https://members-api.parliament.uk/api/Members/999").mock(
            return_value=httpx.Response(
                200,
                json={"value": {"id": 999, "nameDisplayAs": "John Smith"}},
            )
        )

        topic = MagicMock()
        topic.slug = "energy"
        topic.search_queries = ["energy"]

        with httpx.Client() as http:
            client = ParliamentClientSync(http)
            results = client.discover_for_topic(topic)

        assert len(results["questions"]) == 1
        assert len(results["members"]) == 1
        assert results["members"][0]["nameDisplayAs"] == "John Smith"
