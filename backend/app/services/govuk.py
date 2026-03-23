from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from app.services.topic_rules import (
    build_topic_keyword_rules,
    compile_candidate_text,
    expand_upstream_queries,
    has_advanced_keyword_rules,
    matches_topic_rules,
)

if TYPE_CHECKING:
    from app.models.silver import Topic

logger = logging.getLogger(__name__)

GOVUK_BASE = "https://www.gov.uk"


def _matches_govuk_topic_rules(topic: Topic, result: dict) -> bool:
    rules = build_topic_keyword_rules(
        keyword_groups=getattr(topic, "keyword_groups", None),
        excluded_keywords=getattr(topic, "excluded_keywords", None),
        search_queries=getattr(topic, "search_queries", None),
    )
    if not has_advanced_keyword_rules(rules):
        return True
    candidate_text = compile_candidate_text(
        result.get("title"),
        result.get("description"),
        result.get("link"),
        result.get("content_purpose_supergroup"),
        result.get("document_type"),
    )
    return matches_topic_rules(rules, candidate_text)


class GovUkClient:
    """Client for GOV.UK Search and Content APIs."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.http = http_client

    async def search(
        self,
        query: str,
        count: int = 20,
        start: int = 0,
        order: str | None = None,
    ) -> dict:
        """
        Search GOV.UK. Returns raw JSON.

        The Search API is strict about parameters — unknown params return 422.
        We only use documented params: q, count, start, order.
        """
        params: dict[str, str | int] = {
            "q": query,
            "count": count,
            "start": start,
        }
        if order:
            params["order"] = order

        resp = await self.http.get(f"{GOVUK_BASE}/api/search.json", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_content(self, base_path: str) -> dict:
        """Fetch a single content item by its base_path. Returns raw JSON."""
        path = base_path.lstrip("/")
        resp = await self.http.get(f"{GOVUK_BASE}/api/content/{path}")
        resp.raise_for_status()
        return resp.json()

    async def discover_for_topic(self, topic: Topic) -> list[dict]:
        """
        Run all search queries for a topic, deduplicate by _id,
        return raw search result dicts.
        """
        all_results: list[dict] = []
        seen_ids: set[str] = set()
        rules = build_topic_keyword_rules(
            keyword_groups=getattr(topic, "keyword_groups", None),
            excluded_keywords=getattr(topic, "excluded_keywords", None),
            search_queries=getattr(topic, "search_queries", None),
        )
        queries = expand_upstream_queries(rules)

        for query in queries:
            page = 0
            max_pages = 10  # Safety cap: 500 items per query
            while page < max_pages:
                try:
                    data = await self.search(query, count=50, start=page * 50)
                except httpx.HTTPError as exc:
                    logger.warning(
                        "GOV.UK search failed for query=%r page=%d: %s",
                        query, page, exc,
                    )
                    break

                results = data.get("results", [])
                if not results:
                    break

                for r in results:
                    rid = r.get("_id")
                    if rid and rid not in seen_ids and _matches_govuk_topic_rules(topic, r):
                        seen_ids.add(rid)
                        all_results.append(r)

                total = data.get("total", 0)
                page += 1
                if page * 50 >= total:
                    break

        logger.info(
            "GOV.UK discovery for topic %r: %d unique results from %d queries",
            topic.slug, len(all_results), len(queries),
        )
        return all_results


class GovUkClientSync:
    """Synchronous variant for local refresh execution."""

    def __init__(self, http_client: httpx.Client):
        self.http = http_client

    def search(
        self,
        query: str,
        count: int = 20,
        start: int = 0,
        order: str | None = None,
    ) -> dict:
        params: dict[str, str | int] = {
            "q": query,
            "count": count,
            "start": start,
        }
        if order:
            params["order"] = order

        resp = self.http.get(f"{GOVUK_BASE}/api/search.json", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_content(self, base_path: str) -> dict:
        path = base_path.lstrip("/")
        resp = self.http.get(f"{GOVUK_BASE}/api/content/{path}")
        resp.raise_for_status()
        return resp.json()

    def discover_for_topic(self, topic: Topic) -> list[dict]:
        all_results: list[dict] = []
        seen_ids: set[str] = set()
        rules = build_topic_keyword_rules(
            keyword_groups=getattr(topic, "keyword_groups", None),
            excluded_keywords=getattr(topic, "excluded_keywords", None),
            search_queries=getattr(topic, "search_queries", None),
        )
        queries = expand_upstream_queries(rules)

        for query in queries:
            page = 0
            max_pages = 10
            while page < max_pages:
                try:
                    data = self.search(query, count=50, start=page * 50)
                except httpx.HTTPError as exc:
                    logger.warning(
                        "GOV.UK search failed for query=%r page=%d: %s",
                        query, page, exc,
                    )
                    break

                results = data.get("results", [])
                if not results:
                    break

                for r in results:
                    rid = r.get("_id")
                    if rid and rid not in seen_ids and _matches_govuk_topic_rules(topic, r):
                        seen_ids.add(rid)
                        all_results.append(r)

                total = data.get("total", 0)
                page += 1
                if page * 50 >= total:
                    break

        logger.info(
            "GOV.UK discovery for topic %r: %d unique results from %d queries",
            topic.slug, len(all_results), len(queries),
        )
        return all_results
