from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import TYPE_CHECKING

import httpx

from app.services.topic_rules import (
    build_topic_keyword_rules,
    compile_candidate_text,
    expand_upstream_queries,
    has_advanced_keyword_rules,
    matching_keyword_groups,
)

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


def build_written_question_url(date_tabled: date | None, uin: str | None) -> str | None:
    if not date_tabled or not uin:
        return None
    return (
        "https://questions-statements.parliament.uk/written-questions/"
        f"detail/{date_tabled.isoformat()}/{uin}"
    )


def build_bill_url(parliament_bill_id: int | None) -> str | None:
    if not parliament_bill_id:
        return None
    return f"https://bills.parliament.uk/bills/{parliament_bill_id}"


def _extract_asking_member_ids(questions: list[dict]) -> list[int]:
    member_ids = {
        member_id
        for question in questions
        for member_id in [question.get("askingMemberId")]
        if member_id
    }
    return sorted(member_ids)


def _matched_bill_rule_groups(topic: Topic, bill: dict) -> list[list[str]] | None:
    rules = build_topic_keyword_rules(
        keyword_groups=getattr(topic, "keyword_groups", None),
        excluded_keywords=getattr(topic, "excluded_keywords", None),
        search_queries=getattr(topic, "search_queries", None),
    )
    if not has_advanced_keyword_rules(rules):
        return [list(group) for group in rules.keyword_groups] or None
    return matching_keyword_groups(
        rules,
        compile_candidate_text(
            bill.get("shortTitle"),
            bill.get("longTitle"),
            bill.get("summary"),
        ),
    )


def _matched_question_rule_groups(topic: Topic, question: dict) -> list[list[str]] | None:
    rules = build_topic_keyword_rules(
        keyword_groups=getattr(topic, "keyword_groups", None),
        excluded_keywords=getattr(topic, "excluded_keywords", None),
        search_queries=getattr(topic, "search_queries", None),
    )
    if not has_advanced_keyword_rules(rules):
        return [list(group) for group in rules.keyword_groups] or None
    return matching_keyword_groups(
        rules,
        compile_candidate_text(
            question.get("heading"),
            question.get("questionText"),
            question.get("answerText"),
            question.get("uin"),
        ),
    )


def _matched_division_rule_groups(topic: Topic, division: dict) -> list[list[str]] | None:
    rules = build_topic_keyword_rules(
        keyword_groups=getattr(topic, "keyword_groups", None),
        excluded_keywords=getattr(topic, "excluded_keywords", None),
        search_queries=getattr(topic, "search_queries", None),
    )
    if not has_advanced_keyword_rules(rules):
        return [list(group) for group in rules.keyword_groups] or None
    return matching_keyword_groups(
        rules,
        compile_candidate_text(
            division.get("Title"),
            division.get("Summary"),
            division.get("Date"),
        ),
    )


def _build_discovery_result(
    payload: dict,
    *,
    query: str,
    match_method: str,
    matched_rule_group: list[list[str]] | None,
) -> dict:
    return {
        "payload": payload,
        "match_method": match_method,
        "matched_by_query": query,
        "matched_by_rule_group": matched_rule_group,
    }


class ParliamentClient:
    """Async client wrapping multiple Parliament API endpoints."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.http = http_client

    async def search_members(
        self,
        name: str | None = None,
        location: str | None = None,
        skip: int = 0,
        take: int = 20,
    ) -> dict:
        params: dict[str, str | int] = {"skip": skip, "take": take}
        if name:
            params["Name"] = name
        if location:
            params["Location"] = location
        resp = await self.http.get(f"{MEMBERS_API}/Members/Search", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_member(self, member_id: int) -> dict:
        resp = await self.http.get(f"{MEMBERS_API}/Members/{member_id}")
        resp.raise_for_status()
        return _unwrap_member_payload(resp.json())

    async def get_member_voting(
        self, member_id: int, house: int = 1, skip: int = 0, take: int = 20
    ) -> dict:
        """Fetch divisions an MP voted in via the Members API."""
        params = {"house": house, "skip": skip, "take": take}
        resp = await self.http.get(
            f"{MEMBERS_API}/Members/{member_id}/Voting", params=params
        )
        resp.raise_for_status()
        return resp.json()

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
        rules = build_topic_keyword_rules(
            keyword_groups=getattr(topic, "keyword_groups", None),
            excluded_keywords=getattr(topic, "excluded_keywords", None),
            search_queries=getattr(topic, "search_queries", None),
        )

        for query in expand_upstream_queries(rules):
            await self._discover_bills(topic, query, results, seen)
            await self._discover_questions(topic, query, results, seen)
            await self._discover_divisions(topic, query, results, seen)

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
        self, topic: Topic, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = await self.search_bills(query, take=50)
        except httpx.HTTPError as exc:
            logger.warning("Parliament bills search failed for %r: %s", query, exc)
            return

        for item in data.get("items", []):
            bid = item.get("billId")
            matched_rule_group = _matched_bill_rule_groups(topic, item)
            if bid and bid not in seen["bills"] and matched_rule_group is not None:
                seen["bills"].add(bid)
                results["bills"].append(
                    _build_discovery_result(
                        item,
                        query=query,
                        match_method="parliament_search",
                        matched_rule_group=matched_rule_group,
                    )
                )

    async def _discover_questions(
        self, topic: Topic, query: str, results: dict[str, list], seen: dict[str, set]
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
                new_questions.append(record)

        await self._enrich_questions_with_details(new_questions)
        for record in new_questions:
            matched_rule_group = _matched_question_rule_groups(topic, record)
            if matched_rule_group is not None:
                results["questions"].append(
                    _build_discovery_result(
                        record,
                        query=query,
                        match_method="parliament_search",
                        matched_rule_group=matched_rule_group,
                    )
                )

    async def _discover_divisions(
        self, topic: Topic, query: str, results: dict[str, list], seen: dict[str, set]
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
            matched_rule_group = _matched_division_rule_groups(topic, item)
            if did and did not in seen["divisions"] and matched_rule_group is not None:
                seen["divisions"].add(did)
                results["divisions"].append(
                    _build_discovery_result(
                        item,
                        query=query,
                        match_method="parliament_search",
                        matched_rule_group=matched_rule_group,
                    )
                )

    async def _discover_members(
        self, questions: list[dict], results: dict[str, list], seen: dict[str, set]
    ) -> None:
        for member_id in _extract_asking_member_ids([question["payload"] for question in questions]):
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
        self,
        name: str | None = None,
        location: str | None = None,
        skip: int = 0,
        take: int = 20,
    ) -> dict:
        params: dict[str, str | int] = {"skip": skip, "take": take}
        if name:
            params["Name"] = name
        if location:
            params["Location"] = location
        resp = self.http.get(f"{MEMBERS_API}/Members/Search", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_member(self, member_id: int) -> dict:
        resp = self.http.get(f"{MEMBERS_API}/Members/{member_id}")
        resp.raise_for_status()
        return _unwrap_member_payload(resp.json())

    def get_member_voting(
        self, member_id: int, house: int = 1, skip: int = 0, take: int = 20
    ) -> dict:
        """Fetch divisions an MP voted in via the Members API."""
        params = {"house": house, "skip": skip, "take": take}
        resp = self.http.get(
            f"{MEMBERS_API}/Members/{member_id}/Voting", params=params
        )
        resp.raise_for_status()
        return resp.json()

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
        rules = build_topic_keyword_rules(
            keyword_groups=getattr(topic, "keyword_groups", None),
            excluded_keywords=getattr(topic, "excluded_keywords", None),
            search_queries=getattr(topic, "search_queries", None),
        )

        for query in expand_upstream_queries(rules):
            self._discover_bills(topic, query, results, seen)
            self._discover_questions(topic, query, results, seen)
            self._discover_divisions(topic, query, results, seen)

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
        self, topic: Topic, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = self.search_bills(query, take=50)
        except httpx.HTTPError as exc:
            logger.warning("Parliament bills search failed for %r: %s", query, exc)
            return

        for item in data.get("items", []):
            bid = item.get("billId")
            matched_rule_group = _matched_bill_rule_groups(topic, item)
            if bid and bid not in seen["bills"] and matched_rule_group is not None:
                seen["bills"].add(bid)
                results["bills"].append(
                    _build_discovery_result(
                        item,
                        query=query,
                        match_method="parliament_search",
                        matched_rule_group=matched_rule_group,
                    )
                )

    def _discover_questions(
        self, topic: Topic, query: str, results: dict[str, list], seen: dict[str, set]
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
                new_questions.append(record)

        self._enrich_questions_with_details(new_questions)
        for record in new_questions:
            matched_rule_group = _matched_question_rule_groups(topic, record)
            if matched_rule_group is not None:
                results["questions"].append(
                    _build_discovery_result(
                        record,
                        query=query,
                        match_method="parliament_search",
                        matched_rule_group=matched_rule_group,
                    )
                )

    def _discover_divisions(
        self, topic: Topic, query: str, results: dict[str, list], seen: dict[str, set]
    ) -> None:
        try:
            data = self.search_divisions(query, take=50)
        except httpx.HTTPError as exc:
            logger.warning("Parliament divisions search failed for %r: %s", query, exc)
            return

        items = data if isinstance(data, list) else data.get("items", [])
        for item in items:
            did = item.get("DivisionId")
            matched_rule_group = _matched_division_rule_groups(topic, item)
            if did and did not in seen["divisions"] and matched_rule_group is not None:
                seen["divisions"].add(did)
                results["divisions"].append(
                    _build_discovery_result(
                        item,
                        query=query,
                        match_method="parliament_search",
                        matched_rule_group=matched_rule_group,
                    )
                )

    def _discover_members(
        self, questions: list[dict], results: dict[str, list], seen: dict[str, set]
    ) -> None:
        for member_id in _extract_asking_member_ids([question["payload"] for question in questions]):
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
