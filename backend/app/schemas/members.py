from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MemberSearchResult(BaseModel):
    parliament_id: int
    name_display: str
    party: str | None = None
    house: str | None = None
    constituency: str | None = None
    thumbnail_url: str | None = None
    is_active: bool = True
    is_tracked: bool = False


class MemberSearchResponse(BaseModel):
    results: list[MemberSearchResult]
    total: int


class TrackedMemberSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parliament_id: int
    name_display: str
    party: str | None = None
    house: str | None = None
    constituency: str | None = None
    thumbnail_url: str | None = None
    is_active: bool = True
    last_refreshed_at: datetime | None = None
    vote_count: int = 0
    question_count: int = 0


class TrackedMemberListResponse(BaseModel):
    members: list[TrackedMemberSummary]


class MemberVoteRecord(BaseModel):
    division_id: int
    parliament_division_id: int
    title: str
    date: datetime
    vote: str
    aye_count: int
    no_count: int


class MemberVotesResponse(BaseModel):
    parliament_id: int
    votes: list[MemberVoteRecord]
    total: int
    has_more: bool


class MemberQuestionRecord(BaseModel):
    question_id: int
    heading: str
    uin: str | None = None
    house: str | None = None
    date_tabled: date | None = None
    date_answered: date | None = None
    answering_body: str | None = None
    question_text: str | None = None
    answer_text: str | None = None
    answer_source_url: str | None = None
    official_url: str | None = None


class MemberQuestionsResponse(BaseModel):
    parliament_id: int
    questions: list[MemberQuestionRecord]
    total: int
    has_more: bool
