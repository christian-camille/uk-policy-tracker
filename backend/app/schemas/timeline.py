from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MatchProvenance(BaseModel):
    matched_at: datetime | None = None
    last_matched_at: datetime | None = None
    match_method: str | None = None
    matched_by_query: str | None = None
    matched_by_rule_group: list[list[str]] | None = None
    refresh_run_id: str | None = None


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
    question_uin: str | None = None
    question_text: str | None = None
    question_house: str | None = None
    question_date_tabled: date | None = None
    question_date_answered: date | None = None
    asking_member_name: str | None = None
    question_answer_text: str | None = None
    question_answer_source_url: str | None = None
    question_official_url: str | None = None
    match_provenance: MatchProvenance | None = None


class TimelineResponse(BaseModel):
    topic_id: int
    events: list[TimelineEvent]
    total: int
    has_more: bool
