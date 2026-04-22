from app.database import get_sync_session
from app.models.silver import Topic
from app.tasks.ingest import (
    create_activity_events,
    generate_refresh_run_id,
    ingest_govuk_for_topic,
    ingest_parliament_for_topic,
    rebuild_graph_projection,
    run_entity_matching,
)


def run_topic_refresh(topic_id: int) -> dict:
    with get_sync_session() as db:
        topic = db.get(Topic, topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")

    refresh_run_id = generate_refresh_run_id()

    govuk = ingest_govuk_for_topic(topic_id, refresh_run_id=refresh_run_id)
    parliament = ingest_parliament_for_topic(topic_id, refresh_run_id=refresh_run_id)
    events = create_activity_events(topic_id)
    mentions = run_entity_matching(topic_id)
    graph = rebuild_graph_projection()

    return {
        "refresh_run_id": refresh_run_id,
        "govuk": govuk,
        "parliament": parliament,
        "events": events,
        "mentions": mentions,
        "graph": graph,
    }


def run_all_topic_refreshes() -> dict:
    with get_sync_session() as db:
        topic_ids = [topic_id for (topic_id,) in db.query(Topic.id).filter(Topic.is_global.is_(True))]

    if not topic_ids:
        return {"status": "no_topics", "topics": 0, "results": []}

    results = [{"topic_id": topic_id, "result": run_topic_refresh(topic_id)} for topic_id in topic_ids]
    return {"status": "completed", "topics": len(results), "results": results}