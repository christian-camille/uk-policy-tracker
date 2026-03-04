import re
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models.silver import ActivityEvent, Topic, User
from app.schemas.timeline import TimelineEvent, TimelineResponse
from app.schemas.topics import TopicCreate, TopicListResponse, TopicSummary

router = APIRouter(
    prefix="/topics",
    tags=["topics"],
    dependencies=[Depends(get_current_user)],
)


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


async def _get_user_by_subject(db: AsyncSession, subject: str) -> User | None:
    result = await db.execute(
        select(User).where(
            User.auth_provider == "supabase",
            User.provider_subject == subject,
        )
    )
    return result.scalar_one_or_none()


async def _get_or_create_user(db: AsyncSession, current_user: AuthenticatedUser) -> User:
    user = await _get_user_by_subject(db, current_user.subject)
    if user:
        return user

    user = User(
        auth_provider="supabase",
        provider_subject=current_user.subject,
        email=current_user.email,
        display_name=current_user.email,
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()
    return user


async def _get_accessible_topic(
    db: AsyncSession,
    topic_id: int,
    current_user: AuthenticatedUser,
) -> Topic:
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    if topic.is_global:
        return topic

    owner = await _get_user_by_subject(db, current_user.subject)
    if not owner or topic.owner_user_id != owner.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return topic


@router.get("", response_model=TopicListResponse)
async def list_topics(
    scope: Literal["all", "shared", "private"] = Query("all"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all topics with last refresh time and new items count."""
    user = await _get_user_by_subject(db, current_user.subject)

    if scope == "shared":
        visibility_filter = Topic.is_global.is_(True)
    elif scope == "private":
        if not user:
            return TopicListResponse(topics=[])
        visibility_filter = Topic.owner_user_id == user.id
    else:
        if user:
            visibility_filter = or_(
                Topic.is_global.is_(True),
                Topic.owner_user_id == user.id,
            )
        else:
            visibility_filter = Topic.is_global.is_(True)

    new_items_subq = (
        select(func.count(ActivityEvent.id))
        .where(ActivityEvent.topic_id == Topic.id)
        .correlate(Topic)
        .scalar_subquery()
    )
    stmt = (
        select(Topic, new_items_subq.label("new_items_count"))
        .where(visibility_filter)
        .order_by(Topic.label)
    )
    result = await db.execute(stmt)

    topics = []
    for topic, new_items_count in result:
        summary = TopicSummary.model_validate(topic)
        summary.new_items_count = new_items_count or 0
        topics.append(summary)

    return TopicListResponse(topics=topics)


@router.post("", response_model=TopicSummary, status_code=201)
async def create_topic(
    payload: TopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Add a new topic to the watchlist."""
    slug = _slugify(payload.label)
    owner_user_id: int | None = None

    if payload.is_global:
        existing_stmt = select(Topic).where(
            Topic.slug == slug,
            Topic.is_global.is_(True),
        )
    else:
        owner = await _get_or_create_user(db, current_user)
        owner_user_id = owner.id
        existing_stmt = select(Topic).where(
            Topic.slug == slug,
            Topic.is_global.is_(False),
            Topic.owner_user_id == owner_user_id,
        )

    existing = await db.execute(existing_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Topic with slug '{slug}' already exists")

    topic = Topic(
        slug=slug,
        label=payload.label,
        search_queries=payload.search_queries,
        is_global=payload.is_global,
        owner_user_id=owner_user_id,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)

    summary = TopicSummary.model_validate(topic)
    summary.new_items_count = 0
    return summary


@router.get("/{topic_id}", response_model=TopicSummary)
async def get_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single topic by ID."""
    topic = await _get_accessible_topic(db, topic_id, current_user)

    count_result = await db.execute(
        select(func.count(ActivityEvent.id)).where(ActivityEvent.topic_id == topic_id)
    )
    new_items_count = count_result.scalar() or 0

    summary = TopicSummary.model_validate(topic)
    summary.new_items_count = new_items_count
    return summary


@router.get("/{topic_id}/timeline", response_model=TimelineResponse)
async def get_topic_timeline(
    topic_id: int,
    since: str | None = Query(None, description="ISO datetime to filter events after"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Return ActivityEvents for a topic, ordered by event_date desc."""
    await _get_accessible_topic(db, topic_id, current_user)

    base_filter = ActivityEvent.topic_id == topic_id
    if since:
        from datetime import datetime

        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' datetime format")
        base_filter = base_filter & (ActivityEvent.event_date >= since_dt)

    count_stmt = select(func.count(ActivityEvent.id)).where(base_filter)
    total = (await db.execute(count_stmt)).scalar() or 0

    events_stmt = (
        select(ActivityEvent)
        .where(base_filter)
        .order_by(ActivityEvent.event_date.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(events_stmt)
    events = [TimelineEvent.model_validate(row) for row in result.scalars()]

    return TimelineResponse(
        topic_id=topic_id,
        events=events,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.post("/{topic_id}/refresh", status_code=202)
async def trigger_refresh(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Trigger an on-demand refresh of a topic's data."""
    await _get_accessible_topic(db, topic_id, current_user)

    from app.tasks.pipeline import refresh_single_topic

    refresh_single_topic.delay(topic_id)
    return {"status": "queued", "topic_id": topic_id}


@router.get("/{topic_id}/actors")
async def get_topic_actors(
    topic_id: int,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Return key actors (persons) most connected to a topic."""
    await _get_accessible_topic(db, topic_id, current_user)

    from app.services.graph import GraphService

    service = GraphService(db)
    actors = await service.get_key_actors(topic_id, limit=limit)
    return actors


@router.delete("/{topic_id}", status_code=204)
async def remove_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Remove a topic from the watchlist."""
    topic = await _get_accessible_topic(db, topic_id, current_user)

    if topic.is_global:
        raise HTTPException(
            status_code=403,
            detail="Shared topics cannot be deleted",
        )

    await db.delete(topic)
    await db.commit()
