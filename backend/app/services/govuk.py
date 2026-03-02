from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.models.silver import Topic

logger = logging.getLogger(__name__)

GOVUK_BASE = "https://www.gov.uk"


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

        for query in topic.search_queries:
            page = 0
            max_pages = 10  # Safety cap: 500 items per query
            while page < max_pages:
                try:
                    data = await self.search(query, count=50, start=page * 50)
                except httpx.HTTPStatusError as exc:
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
                    if rid and rid not in seen_ids:
                        seen_ids.add(rid)
                        all_results.append(r)

                total = data.get("total", 0)
                page += 1
                if page * 50 >= total:
                    break

        logger.info(
            "GOV.UK discovery for topic %r: %d unique results from %d queries",
            topic.slug, len(all_results), len(topic.search_queries),
        )
        return all_results


class GovUkClientSync:
    """Synchronous variant for use inside Celery workers."""

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

        for query in topic.search_queries:
            page = 0
            max_pages = 10
            while page < max_pages:
                try:
                    data = self.search(query, count=50, start=page * 50)
                except httpx.HTTPStatusError as exc:
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
                    if rid and rid not in seen_ids:
                        seen_ids.add(rid)
                        all_results.append(r)

                total = data.get("total", 0)
                page += 1
                if page * 50 >= total:
                    break

        logger.info(
            "GOV.UK discovery for topic %r: %d unique results from %d queries",
            topic.slug, len(all_results), len(topic.search_queries),
        )
        return all_results
