from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TimelineEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    event_date: datetime
    title: str
    summary: str | None
    source_url: str | None
    source_entity_type: str
    source_entity_id: int


class TimelineResponse(BaseModel):
    topic_id: int
    events: list[TimelineEvent]
    total: int
    has_more: bool
