from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TopicKeywordRules:
    keyword_groups: list[list[str]]
    excluded_keywords: list[str]

    @property
    def search_queries(self) -> list[str]:
        queries: list[str] = []
        for group in self.keyword_groups:
            for keyword in group:
                if keyword not in queries:
                    queries.append(keyword)
        return queries


def _coerce_list(value: object) -> list[Any]:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return []

        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, list):
            return parsed

        return [part.strip() for part in normalized.split(",") if part.strip()]

    return []


def normalize_keyword_groups(value: object) -> list[list[str]]:
    groups: list[list[str]] = []
    raw_groups = _coerce_list(value)

    if raw_groups and all(isinstance(item, str) for item in raw_groups):
        raw_groups = [raw_groups]

    for raw_group in raw_groups:
        entries = [str(entry).strip() for entry in _coerce_list(raw_group) if str(entry).strip()]
        deduped: list[str] = []
        seen: set[str] = set()
        for entry in entries:
            lowered = entry.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(entry)
        if deduped:
            groups.append(deduped)

    return groups


def normalize_keywords(value: object) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in _coerce_list(value):
        text = str(item).strip()
        if not text:
            continue
        lowered = text.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(text)
    return normalized


def build_topic_keyword_rules(
    *,
    keyword_groups: object = None,
    excluded_keywords: object = None,
    search_queries: object = None,
) -> TopicKeywordRules:
    normalized_groups = normalize_keyword_groups(keyword_groups)
    normalized_excluded = normalize_keywords(excluded_keywords)

    if not normalized_groups:
        legacy_queries = normalize_keywords(search_queries)
        if legacy_queries:
            normalized_groups = [legacy_queries]

    return TopicKeywordRules(
        keyword_groups=normalized_groups,
        excluded_keywords=normalized_excluded,
    )


def validate_topic_keyword_rules(rules: TopicKeywordRules) -> None:
    if not rules.keyword_groups:
        raise ValueError("Topic keyword groups cannot be empty")

    if any(not group for group in rules.keyword_groups):
        raise ValueError("Topic keyword groups cannot contain empty groups")


def expand_upstream_queries(rules: TopicKeywordRules) -> list[str]:
    return rules.search_queries


def has_advanced_keyword_rules(rules: TopicKeywordRules) -> bool:
    return len(rules.keyword_groups) > 1 or bool(rules.excluded_keywords)


def compile_candidate_text(*parts: object) -> str:
    text_parts = [str(part).strip().casefold() for part in parts if str(part).strip()]
    return "\n".join(text_parts)


def matches_topic_rules(rules: TopicKeywordRules, candidate_text: str) -> bool:
    return matching_keyword_groups(rules, candidate_text) is not None


def matching_keyword_groups(
    rules: TopicKeywordRules, candidate_text: str
) -> list[list[str]] | None:
    haystack = candidate_text.casefold()
    if not haystack:
        return False

    for keyword in rules.excluded_keywords:
        if keyword.casefold() in haystack:
            return None

    matched_groups: list[list[str]] = []
    for group in rules.keyword_groups:
        if not any(keyword.casefold() in haystack for keyword in group):
            return None
        matched_groups.append(list(group))

    return matched_groups