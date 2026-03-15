from __future__ import annotations

import asyncio
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


def _unwrap_member_payload(payload: dict) -> dict:
    return payload.get("value", payload)


def _unwrap_question_payload(payload: dict) -> dict:
    return payload.get("value", payload)


def _extract_asking_member_ids(questions: list[dict]) -> list[int]:
    member_ids = {
        member_id
        for question in questions
        for member_id in [question.get("askingMemberId")]
        if member_id
    }
    return sorted(member_ids)


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

    async def get_member(self, member_id: int) -> dict:
        resp = await self.http.get(f"{MEMBERS_API}/Members/{member_id}")
        resp.raise_for_status()
        return _unwrap_member_payload(resp.json())

    async def get_question(self, question_id: int) -> dict:
        resp = await self.http.get(
            f"{QUESTIONS_API}/writtenquestions/questions/{question_id}"
        )
        resp.raise_for_status()
        return _unwrap_question_payload(resp.json())

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

        await self._discover_members(results["questions"], results, seen)

        logger.info(
            "Parliament discovery for topic %r: bills=%d, members=%d, questions=%d, divisions=%d",
            topic.slug,
            len(results["bills"]),
            len(results["members"]),
            len(results["questions"]),
            len(results["divisions"]),
        )
        return results

    async def _discover_bills(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = await self.search_bills(query, take=50)
        except httpx.HTTPError as exc:
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
        except httpx.HTTPError as exc:
            logger.warning("Parliament questions search failed for %r: %s", query, exc)
            return

        new_questions: list[dict] = []
        for item in data.get("results", []):
            record = item.get("value", item)
            qid = record.get("id")
            if qid and qid not in seen["questions"]:
                seen["questions"].add(qid)
                results["questions"].append(record)
                new_questions.append(record)

        await self._enrich_questions_with_details(new_questions)

    async def _discover_divisions(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = await self.search_divisions(query, take=50)
        except httpx.HTTPError as exc:
            logger.warning("Parliament divisions search failed for %r: %s", query, exc)
            return

        # Divisions API returns a top-level array
        items = data if isinstance(data, list) else data.get("items", [])
        for item in items:
            did = item.get("DivisionId")
            if did and did not in seen["divisions"]:
                seen["divisions"].add(did)
                results["divisions"].append(item)

    async def _discover_members(
        self, questions: list[dict], results: dict[str, list], seen: dict[str, set]
    ) -> None:
        for member_id in _extract_asking_member_ids(questions):
            if member_id in seen["members"]:
                continue
            try:
                member = await self.get_member(member_id)
            except httpx.HTTPError as exc:
                logger.warning("Parliament member lookup failed for %r: %s", member_id, exc)
                continue

            normalized_member = _unwrap_member_payload(member)
            normalized_member_id = normalized_member.get("id")
            if normalized_member_id and normalized_member_id not in seen["members"]:
                seen["members"].add(normalized_member_id)
                results["members"].append(normalized_member)

    async def _enrich_questions_with_details(self, questions: list[dict]) -> None:
        detail_candidates = [
            question
            for question in questions
            if question.get("id") and question.get("dateAnswered")
        ]
        if not detail_candidates:
            return

        results = await asyncio.gather(
            *[self.get_question(question["id"]) for question in detail_candidates],
            return_exceptions=True,
        )
        for question, detail in zip(detail_candidates, results, strict=False):
            if isinstance(detail, Exception):
                logger.warning(
                    "Parliament question detail lookup failed for %r: %s",
                    question.get("id"),
                    detail,
                )
                continue
            question.update(detail)


class ParliamentClientSync:
    """Synchronous variant for local refresh execution."""

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

    def get_member(self, member_id: int) -> dict:
        resp = self.http.get(f"{MEMBERS_API}/Members/{member_id}")
        resp.raise_for_status()
        return _unwrap_member_payload(resp.json())

    def get_question(self, question_id: int) -> dict:
        resp = self.http.get(
            f"{QUESTIONS_API}/writtenquestions/questions/{question_id}"
        )
        resp.raise_for_status()
        return _unwrap_question_payload(resp.json())

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

        self._discover_members(results["questions"], results, seen)

        logger.info(
            "Parliament discovery for topic %r: bills=%d, members=%d, questions=%d, divisions=%d",
            topic.slug,
            len(results["bills"]),
            len(results["members"]),
            len(results["questions"]),
            len(results["divisions"]),
        )
        return results

    def _discover_bills(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = self.search_bills(query, take=50)
        except httpx.HTTPError as exc:
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
        except httpx.HTTPError as exc:
            logger.warning("Parliament questions search failed for %r: %s", query, exc)
            return

        new_questions: list[dict] = []
        for item in data.get("results", []):
            record = item.get("value", item)
            qid = record.get("id")
            if qid and qid not in seen["questions"]:
                seen["questions"].add(qid)
                results["questions"].append(record)
                new_questions.append(record)

        self._enrich_questions_with_details(new_questions)

    def _discover_divisions(
        self, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = self.search_divisions(query, take=50)
        except httpx.HTTPError as exc:
            logger.warning("Parliament divisions search failed for %r: %s", query, exc)
            return

        items = data if isinstance(data, list) else data.get("items", [])
        for item in items:
            did = item.get("DivisionId")
            if did and did not in seen["divisions"]:
                seen["divisions"].add(did)
                results["divisions"].append(item)

    def _discover_members(
        self, questions: list[dict], results: dict[str, list], seen: dict[str, set]
    ) -> None:
        for member_id in _extract_asking_member_ids(questions):
            if member_id in seen["members"]:
                continue
            try:
                member = self.get_member(member_id)
            except httpx.HTTPError as exc:
                logger.warning("Parliament member lookup failed for %r: %s", member_id, exc)
                continue

            normalized_member = _unwrap_member_payload(member)
            normalized_member_id = normalized_member.get("id")
            if normalized_member_id and normalized_member_id not in seen["members"]:
                seen["members"].add(normalized_member_id)
                results["members"].append(normalized_member)

    def _enrich_questions_with_details(self, questions: list[dict]) -> None:
        for question in questions:
            question_id = question.get("id")
            if not question_id or not question.get("dateAnswered"):
                continue
            try:
                detail = self.get_question(question_id)
            except httpx.HTTPError as exc:
                logger.warning(
                    "Parliament question detail lookup failed for %r: %s",
                    question_id,
                    exc,
                )
                continue
            question.update(detail)
