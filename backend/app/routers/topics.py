import re
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.silver import (
    ActivityEvent,
    BillTopic,
    ContentItemTopic,
    DivisionTopic,
    Person,
    QuestionTopic,
    Topic,
    WrittenQuestion,
)
from app.schemas.timeline import MatchProvenance, TimelineEvent, TimelineResponse
from app.services.parliament import build_written_question_url
from app.schemas.topics import TopicCreate, TopicListResponse, TopicSummary, TopicUpdate
from app.services.refresh import run_all_topic_refreshes, run_topic_refresh
from app.services.topic_rules import build_topic_keyword_rules, validate_topic_keyword_rules

router = APIRouter(prefix="/topics", tags=["topics"])


async def _load_question_details(
    db: AsyncSession, events: list[ActivityEvent]
) -> dict[int, dict[str, object | None]]:
    question_ids = [
        event.source_entity_id
        for event in events
        if event.source_entity_type == "question"
    ]
    if not question_ids:
        return {}

    stmt = (
        select(
            WrittenQuestion.id,
            WrittenQuestion.uin,
            WrittenQuestion.question_text,
            WrittenQuestion.house,
            WrittenQuestion.date_tabled,
            WrittenQuestion.date_answered,
            WrittenQuestion.answer_text,
            WrittenQuestion.answer_source_url,
            Person.name_display.label("asking_member_name"),
        )
        .outerjoin(Person, Person.parliament_id == WrittenQuestion.asking_member_id)
        .where(WrittenQuestion.id.in_(question_ids))
    )
    result = await db.execute(stmt)
    return {
        row.id: {
            "question_uin": row.uin,
            "question_text": row.question_text,
            "question_house": row.house,
            "question_date_tabled": row.date_tabled,
            "question_date_answered": row.date_answered,
            "asking_member_name": row.asking_member_name,
            "question_answer_text": row.answer_text,
            "question_answer_source_url": row.answer_source_url,
            "question_official_url": build_written_question_url(
                row.date_tabled, row.uin
            ),
        }
        for row in result
    }


async def _load_match_provenance(
    db: AsyncSession, topic_id: int, events: list[ActivityEvent]
) -> dict[tuple[str, int], MatchProvenance]:
    entity_ids_by_type: dict[str, set[int]] = {
        "content_item": set(),
        "bill": set(),
        "question": set(),
        "division": set(),
    }
    for event in events:
        entity_ids = entity_ids_by_type.get(event.source_entity_type)
        if entity_ids is not None:
            entity_ids.add(event.source_entity_id)

    provenance: dict[tuple[str, int], MatchProvenance] = {}
    query_specs = [
        ("content_item", ContentItemTopic, ContentItemTopic.content_item_id),
        ("bill", BillTopic, BillTopic.bill_id),
        ("question", QuestionTopic, QuestionTopic.question_id),
        ("division", DivisionTopic, DivisionTopic.division_id),
    ]

    for source_entity_type, model, entity_column in query_specs:
        entity_ids = entity_ids_by_type[source_entity_type]
        if not entity_ids:
            continue

        stmt = select(model).where(model.topic_id == topic_id, entity_column.in_(entity_ids))
        result = await db.execute(stmt)
        for row in result.scalars():
            provenance[(source_entity_type, getattr(row, entity_column.key))] = MatchProvenance(
                matched_at=row.matched_at,
                last_matched_at=row.last_matched_at,
                match_method=row.match_method,
                matched_by_query=row.matched_by_query,
                matched_by_rule_group=row.matched_by_rule_group,
                refresh_run_id=row.refresh_run_id,
            )

    return provenance


def _parse_iso_datetime(value: str, *, field_name: str, end_of_day: bool = False) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid '{field_name}' datetime format",
        ) from exc

    if end_of_day and "T" not in value:
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)

    return parsed


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _to_topic_summary(topic: Topic, new_items_count: int) -> TopicSummary:
    rules = build_topic_keyword_rules(
        keyword_groups=topic.keyword_groups,
        excluded_keywords=topic.excluded_keywords,
        search_queries=topic.search_queries,
    )
    return TopicSummary(
        id=topic.id,
        slug=topic.slug,
        label=topic.label,
        search_queries=rules.search_queries,
        keyword_groups=rules.keyword_groups,
        excluded_keywords=rules.excluded_keywords,
        is_global=topic.is_global,
        last_refreshed_at=topic.last_refreshed_at,
        new_items_count=new_items_count,
    )


async def _get_topic_or_404(db: AsyncSession, topic_id: int) -> Topic:
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.get("", response_model=TopicListResponse)
async def list_topics(
    scope: Literal["all", "shared", "private"] = Query("all"),
    db: AsyncSession = Depends(get_db),
):
    """List all topics with last refresh time and new items count."""
    if scope == "private":
        return TopicListResponse(topics=[])

    new_items_subq = (
        select(func.count(ActivityEvent.id))
        .where(ActivityEvent.topic_id == Topic.id)
        .correlate(Topic)
        .scalar_subquery()
    )
    stmt = (
        select(Topic, new_items_subq.label("new_items_count"))
        .where(Topic.is_global.is_(True))
        .order_by(Topic.label)
    )
    result = await db.execute(stmt)

    topics = []
    for topic, new_items_count in result:
        topics.append(_to_topic_summary(topic, new_items_count or 0))

    return TopicListResponse(topics=topics)


@router.post("", response_model=TopicSummary, status_code=201)
async def create_topic(
    payload: TopicCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new topic to the watchlist."""
    slug = _slugify(payload.label)
    if not slug:
        raise HTTPException(status_code=400, detail="Topic label is invalid")

    rules = build_topic_keyword_rules(
        keyword_groups=payload.keyword_groups,
        excluded_keywords=payload.excluded_keywords,
        search_queries=payload.search_queries,
    )
    try:
        validate_topic_keyword_rules(rules)
    except ValueError as exc:
        if payload.search_queries is not None and payload.keyword_groups is None and not rules.keyword_groups:
            raise HTTPException(status_code=400, detail="Topic search queries cannot be empty") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing_stmt = select(Topic).where(Topic.slug == slug)

    existing = await db.execute(existing_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Topic with slug '{slug}' already exists")

    topic = Topic(
        slug=slug,
        label=payload.label.strip(),
        search_queries=rules.search_queries,
        keyword_groups=rules.keyword_groups,
        excluded_keywords=rules.excluded_keywords,
        is_global=True,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)

    return _to_topic_summary(topic, 0)


@router.post("/refresh-all")
async def trigger_refresh_all_topics():
    """Trigger an on-demand refresh of all tracked topics."""
    return run_all_topic_refreshes()


@router.get("/{topic_id}", response_model=TopicSummary)
async def get_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single topic by ID."""
    topic = await _get_topic_or_404(db, topic_id)

    count_result = await db.execute(
        select(func.count(ActivityEvent.id)).where(ActivityEvent.topic_id == topic_id)
    )
    new_items_count = count_result.scalar() or 0

    return _to_topic_summary(topic, new_items_count)


@router.patch("/{topic_id}", response_model=TopicSummary)
async def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing topic label and/or search queries."""
    if (
        payload.label is None
        and payload.search_queries is None
        and payload.keyword_groups is None
        and payload.excluded_keywords is None
    ):
        raise HTTPException(status_code=400, detail="No topic fields provided for update")

    topic = await _get_topic_or_404(db, topic_id)

    if payload.label is not None:
        normalized_label = payload.label.strip()
        if not normalized_label:
            raise HTTPException(status_code=400, detail="Topic label cannot be empty")

        next_slug = _slugify(normalized_label)
        if not next_slug:
            raise HTTPException(status_code=400, detail="Topic label is invalid")

        if next_slug != topic.slug:
            existing_stmt = select(Topic).where(Topic.slug == next_slug, Topic.id != topic_id)
            existing = await db.execute(existing_stmt)
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail=f"Topic with slug '{next_slug}' already exists")

        topic.label = normalized_label
        topic.slug = next_slug

    if payload.search_queries is not None or payload.keyword_groups is not None or payload.excluded_keywords is not None:
        existing_rules = build_topic_keyword_rules(
            keyword_groups=topic.keyword_groups,
            excluded_keywords=topic.excluded_keywords,
            search_queries=topic.search_queries,
        )
        next_keyword_groups = payload.keyword_groups
        if next_keyword_groups is None and payload.search_queries is None:
            next_keyword_groups = existing_rules.keyword_groups

        rules = build_topic_keyword_rules(
            keyword_groups=next_keyword_groups,
            excluded_keywords=(payload.excluded_keywords if payload.excluded_keywords is not None else existing_rules.excluded_keywords),
            search_queries=(payload.search_queries if payload.search_queries is not None else existing_rules.search_queries),
        )
        try:
            validate_topic_keyword_rules(rules)
        except ValueError as exc:
            if payload.search_queries is not None and payload.keyword_groups is None and not rules.keyword_groups:
                raise HTTPException(status_code=400, detail="Topic search queries cannot be empty") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        topic.search_queries = rules.search_queries
        topic.keyword_groups = rules.keyword_groups
        topic.excluded_keywords = rules.excluded_keywords

    await db.commit()
    await db.refresh(topic)

    count_result = await db.execute(
        select(func.count(ActivityEvent.id)).where(ActivityEvent.topic_id == topic_id)
    )
    new_items_count = count_result.scalar() or 0

    return _to_topic_summary(topic, new_items_count)


@router.get("/{topic_id}/timeline", response_model=TimelineResponse)
async def get_topic_timeline(
    topic_id: int,
    since: str | None = Query(None, description="ISO datetime to filter events after"),
    until: str | None = Query(None, description="ISO datetime to filter events before"),
    event_type: list[str] | None = Query(None, description="Filter by event type"),
    source_entity_type: list[str] | None = Query(None, description="Filter by source entity type"),
    q: str | None = Query(None, min_length=1, description="Case-insensitive text search"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return ActivityEvents for a topic, ordered by event_date desc."""
    await _get_topic_or_404(db, topic_id)

    filters = [ActivityEvent.topic_id == topic_id]

    if since:
        since_dt = _parse_iso_datetime(since, field_name="since")
        filters.append(ActivityEvent.event_date >= since_dt)

    if until:
        until_dt = _parse_iso_datetime(until, field_name="until", end_of_day=True)
        filters.append(ActivityEvent.event_date <= until_dt)

        if since and since_dt > until_dt:
            raise HTTPException(status_code=400, detail="'since' must be earlier than or equal to 'until'")

    if event_type:
        filters.append(ActivityEvent.event_type.in_(event_type))

    if source_entity_type:
        filters.append(ActivityEvent.source_entity_type.in_(source_entity_type))

    search_query = q.strip() if q else None
    if search_query:
        search_pattern = f"%{search_query}%"
        filters.append(
            or_(
                ActivityEvent.title.ilike(search_pattern),
                func.coalesce(ActivityEvent.summary, "").ilike(search_pattern),
            )
        )

    count_stmt = select(func.count(ActivityEvent.id)).where(*filters)
    total = (await db.execute(count_stmt)).scalar() or 0

    events_stmt = (
        select(ActivityEvent)
        .where(*filters)
        .order_by(ActivityEvent.event_date.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(events_stmt)
    raw_events = list(result.scalars())
    question_details = await _load_question_details(db, raw_events)
    match_provenance = await _load_match_provenance(db, topic_id, raw_events)
    events = [
        TimelineEvent(
            id=event.id,
            event_type=event.event_type,
            event_date=event.event_date,
            title=event.title,
            summary=event.summary,
            source_url=event.source_url,
            source_entity_type=event.source_entity_type,
            source_entity_id=event.source_entity_id,
            **(
                question_details.get(event.source_entity_id, {})
                if event.source_entity_type == "question"
                else {}
            ),
            match_provenance=match_provenance.get(
                (event.source_entity_type, event.source_entity_id)
            ),
        )
        for event in raw_events
    ]

    return TimelineResponse(
        topic_id=topic_id,
        events=events,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.post("/{topic_id}/refresh")
async def trigger_refresh(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an on-demand refresh of a topic's data."""
    await _get_topic_or_404(db, topic_id)
    result = run_topic_refresh(topic_id)
    return {"status": "completed", "topic_id": topic_id, "result": result}


@router.get("/{topic_id}/actors")
async def get_topic_actors(
    topic_id: int,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Return key actors (persons) most connected to a topic."""
    await _get_topic_or_404(db, topic_id)

    from app.services.graph import GraphService

    service = GraphService(db)
    actors = await service.get_key_actors(topic_id, limit=limit)
    return actors


@router.delete("/{topic_id}", status_code=204)
async def remove_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Remove a topic from the watchlist."""
    topic = await _get_topic_or_404(db, topic_id)

    await db.delete(topic)
    await db.commit()
