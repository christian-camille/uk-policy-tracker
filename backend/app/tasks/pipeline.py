from app.tasks.celery_app import celery_app


@celery_app.task
def refresh_single_topic(topic_id: int):
    """Stub: on-demand refresh for a single topic. Implemented in Phase 7."""
    return {"status": "not_implemented", "topic_id": topic_id}


@celery_app.task
def daily_refresh_all_topics():
    """Stub: daily refresh for all topics. Implemented in Phase 7."""
    return {"status": "not_implemented"}
