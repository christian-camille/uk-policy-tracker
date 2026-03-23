from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.topic_rules import (
    build_topic_keyword_rules,
)


class TopicCreate(BaseModel):
    label: str
    search_queries: list[str] | None = None
    keyword_groups: list[list[str]] | None = None
    excluded_keywords: list[str] = Field(default_factory=list)
    is_global: bool = True

    @model_validator(mode="after")
    def validate_rules(self) -> "TopicCreate":
        rules = build_topic_keyword_rules(
            keyword_groups=self.keyword_groups,
            excluded_keywords=self.excluded_keywords,
            search_queries=self.search_queries,
        )
        self.keyword_groups = rules.keyword_groups
        self.excluded_keywords = rules.excluded_keywords
        self.search_queries = rules.search_queries
        return self


class TopicUpdate(BaseModel):
    label: str | None = None
    search_queries: list[str] | None = None
    keyword_groups: list[list[str]] | None = None
    excluded_keywords: list[str] | None = None

    @model_validator(mode="after")
    def normalize_rules(self) -> "TopicUpdate":
        rules = build_topic_keyword_rules(
            keyword_groups=self.keyword_groups,
            excluded_keywords=self.excluded_keywords,
            search_queries=self.search_queries,
        )
        if self.keyword_groups is not None:
            self.keyword_groups = rules.keyword_groups
            self.search_queries = rules.search_queries
        elif self.search_queries is not None:
            self.search_queries = rules.search_queries
        if self.excluded_keywords is not None:
            self.excluded_keywords = rules.excluded_keywords
        return self


class TopicSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    label: str
    search_queries: list[str]
    keyword_groups: list[list[str]]
    excluded_keywords: list[str]
    is_global: bool
    last_refreshed_at: datetime | None
    new_items_count: int = 0


class TopicListResponse(BaseModel):
    topics: list[TopicSummary]
