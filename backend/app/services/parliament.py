from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.models.silver import Topic

logger = logging.getLogger(__name__)

MEMBERS_API = "https://members-api.parliament.uk/api"
BILLS_API = "https://bills-api.parliament.uk/api/v1"
QUESTIONS_API = "https://questions-statements-api.parliament.uk/api"
DIVISIONS_API = "https://commonsvotes-api.parliament.uk/data"


class ParliamentClient:
    """Async client wrapping multiple Parliament API endpoints."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.http = http_client

    async def search_members(
        self, name: str | None = None, skip: int = 0, take: int = 20
    ) -> dict:
        params: dict[str, str | int] = {"skip": skip, "take": take}
        if name:
            params["Name"] = name
        resp = await self.http.get(f"{MEMBERS_API}/Members/Search", params=params)
        resp.raise_for_status()
        return resp.json()

    async def search_bills(
        self, search_term: str, skip: int = 0, take: int = 20
    ) -> dict:
        params = {"SearchTerm": search_term, "Skip": skip, "Take": take}
        resp = await self.http.get(f"{BILLS_API}/Bills", params=params)
        resp.raise_for_status()
        return resp.json()

    async def search_questions(
        self, search_term: str, skip: int = 0, take: int = 20
    ) -> dict:
        params = {"searchTerm": search_term, "skip": skip, "take": take}
        resp = await self.http.get(
            f"{QUESTIONS_API}/writtenquestions/questions", params=params
        )
        resp.raise_for_status()
        return resp.json()

    async def search_divisions(
        self, search_term: str, skip: int = 0, take: int = 20
    ) -> dict:
        params = {
            "queryParameters.searchTerm": search_term,
            "queryParameters.skip": skip,
            "queryParameters.take": take,
        }
        resp = await self.http.get(f"{DIVISIONS_API}/divisions.json/search", params=params)
        resp.raise_for_status()
        return resp.json()

    async def discover_for_topic(self, topic: Topic) -> dict[str, list]:
        """
        Query all Parliament APIs for each search query in a topic.
        Returns {'bills': [...], 'members': [...], 'questions': [...], 'divisions': [...]}.
        Each item is the raw record dict (unwrapped from 'value' nesting where applicable).
        """
        results: dict[str, list] = {
            "bills": [],
            "members": [],
            "questions": [],
            "divisions": [],
        }
        seen: dict[str, set] = {
            "bills": set(),
            "members": set(),
            "questions": set(),
            "divisions": set(),
        }

        for query in topic.search_queries:
            await self._discover_bills(query, results, seen)
            await self._discover_questions(query, results, seen)
            await self._discover_divisions(query, results, seen)

        logger.info(
            "Parliament discovery for topic %r: bills=%d, questions=%d, divisions=%d",
            topic.slug,
            len(results["bills"]),
            len(results["questions"]),
            len(results["divisions"]),
        )
        return results

    async def _discover_bills(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = await self.search_bills(query, take=50)
        except httpx.HTTPStatusError as exc:
            logger.warning("Parliament bills search failed for %r: %s", query, exc)
            return

        for item in data.get("items", []):
            bid = item.get("billId")
            if bid and bid not in seen["bills"]:
                seen["bills"].add(bid)
                results["bills"].append(item)

    async def _discover_questions(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = await self.search_questions(query, take=50)
        except httpx.HTTPStatusError as exc:
            logger.warning("Parliament questions search failed for %r: %s", query, exc)
            return

        for item in data.get("results", []):
            record = item.get("value", item)
            qid = record.get("id")
            if qid and qid not in seen["questions"]:
                seen["questions"].add(qid)
                results["questions"].append(record)

    async def _discover_divisions(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = await self.search_divisions(query, take=50)
        except httpx.HTTPStatusError as exc:
            logger.warning("Parliament divisions search failed for %r: %s", query, exc)
            return

        # Divisions API returns a top-level array
        items = data if isinstance(data, list) else data.get("items", [])
        for item in items:
            did = item.get("DivisionId")
            if did and did not in seen["divisions"]:
                seen["divisions"].add(did)
                results["divisions"].append(item)


class ParliamentClientSync:
    """Synchronous variant for use inside Celery workers."""

    def __init__(self, http_client: httpx.Client):
        self.http = http_client

    def search_members(
        self, name: str | None = None, skip: int = 0, take: int = 20
    ) -> dict:
        params: dict[str, str | int] = {"skip": skip, "take": take}
        if name:
            params["Name"] = name
        resp = self.http.get(f"{MEMBERS_API}/Members/Search", params=params)
        resp.raise_for_status()
        return resp.json()

    def search_bills(
        self, search_term: str, skip: int = 0, take: int = 20
    ) -> dict:
        params = {"SearchTerm": search_term, "Skip": skip, "Take": take}
        resp = self.http.get(f"{BILLS_API}/Bills", params=params)
        resp.raise_for_status()
        return resp.json()

    def search_questions(
        self, search_term: str, skip: int = 0, take: int = 20
    ) -> dict:
        params = {"searchTerm": search_term, "skip": skip, "take": take}
        resp = self.http.get(
            f"{QUESTIONS_API}/writtenquestions/questions", params=params
        )
        resp.raise_for_status()
        return resp.json()

    def search_divisions(
        self, search_term: str, skip: int = 0, take: int = 20
    ) -> dict:
        params = {
            "queryParameters.searchTerm": search_term,
            "queryParameters.skip": skip,
            "queryParameters.take": take,
        }
        resp = self.http.get(f"{DIVISIONS_API}/divisions.json/search", params=params)
        resp.raise_for_status()
        return resp.json()

    def discover_for_topic(self, topic: Topic) -> dict[str, list]:
        results: dict[str, list] = {
            "bills": [],
            "members": [],
            "questions": [],
            "divisions": [],
        }
        seen: dict[str, set] = {
            "bills": set(),
            "members": set(),
            "questions": set(),
            "divisions": set(),
        }

        for query in topic.search_queries:
            self._discover_bills(query, results, seen)
            self._discover_questions(query, results, seen)
            self._discover_divisions(query, results, seen)

        logger.info(
            "Parliament discovery for topic %r: bills=%d, questions=%d, divisions=%d",
            topic.slug,
            len(results["bills"]),
            len(results["questions"]),
            len(results["divisions"]),
        )
        return results

    def _discover_bills(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = self.search_bills(query, take=50)
        except httpx.HTTPStatusError as exc:
            logger.warning("Parliament bills search failed for %r: %s", query, exc)
            return

        for item in data.get("items", []):
            bid = item.get("billId")
            if bid and bid not in seen["bills"]:
                seen["bills"].add(bid)
                results["bills"].append(item)

    def _discover_questions(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = self.search_questions(query, take=50)
        except httpx.HTTPStatusError as exc:
            logger.warning("Parliament questions search failed for %r: %s", query, exc)
            return

        for item in data.get("results", []):
            record = item.get("value", item)
            qid = record.get("id")
            if qid and qid not in seen["questions"]:
                seen["questions"].add(qid)
                results["questions"].append(record)

    def _discover_divisions(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = self.search_divisions(query, take=50)
        except httpx.HTTPStatusError as exc:
            logger.warning("Parliament divisions search failed for %r: %s", query, exc)
            return

        items = data if isinstance(data, list) else data.get("items", [])
        for item in items:
            did = item.get("DivisionId")
            if did and did not in seen["divisions"]:
                seen["divisions"].add(did)
                results["divisions"].append(item)
