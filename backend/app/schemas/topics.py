from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TopicCreate(BaseModel):
    label: str
    search_queries: list[str]
    is_global: bool = True


class TopicUpdate(BaseModel):
    label: str | None = None
    search_queries: list[str] | None = None


class TopicSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    label: str
    search_queries: list[str]
    is_global: bool
    last_refreshed_at: datetime | None
    new_items_count: int = 0


class TopicListResponse(BaseModel):
    topics: list[TopicSummary]
