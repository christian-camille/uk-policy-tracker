import logging

from celery import chain, chord, group

from app.database import get_sync_session
from app.models.silver import Topic
from app.tasks.celery_app import celery_app
from app.tasks.ingest import (
    create_activity_events,
    ingest_govuk_for_topic,
    ingest_parliament_for_topic,
    rebuild_graph_projection,
    run_entity_matching,
)

logger = logging.getLogger(__name__)


@celery_app.task
def refresh_single_topic(topic_id: int):
    """On-demand refresh for a single topic: ingest -> events -> match -> graph."""
    pipeline = chain(
        group(
            ingest_govuk_for_topic.si(topic_id, True),
            ingest_parliament_for_topic.si(topic_id, True),
        ),
        create_activity_events.si(topic_id),
        run_entity_matching.si(topic_id),
        rebuild_graph_projection.si(),
    )
    pipeline.apply_async()
    return {"status": "pipeline_started", "topic_id": topic_id}


@celery_app.task
def daily_refresh_all_topics():
    """Daily refresh: ingest shared topics in parallel, then match and rebuild graph."""
    with get_sync_session() as db:
        topic_ids = [
            topic_id
            for (topic_id,) in db.query(Topic.id).filter(Topic.is_global.is_(True)).all()
        ]

    if not topic_ids:
        logger.info("No shared topics configured, skipping daily refresh")
        return {"status": "no_topics"}

    # Phase 1: Ingest all topics in parallel (GOV.UK + Parliament per topic)
    ingest_tasks = group(
        group(
            ingest_govuk_for_topic.si(tid, False),
            ingest_parliament_for_topic.si(tid, False),
        )
        for tid in topic_ids
    )

    # Phase 2: Create activity events for each topic
    event_tasks = group(create_activity_events.si(tid) for tid in topic_ids)

    # Phase 3: Entity matching for each topic
    matching_tasks = group(run_entity_matching.si(tid) for tid in topic_ids)

    # Chain: ingest -> events -> matching -> graph rebuild
    pipeline = chain(
        ingest_tasks,
        event_tasks,
        matching_tasks,
        rebuild_graph_projection.si(),
    )
    pipeline.apply_async()

    logger.info("Daily refresh pipeline started for %d shared topics", len(topic_ids))
    return {"status": "pipeline_started", "topics": len(topic_ids)}
