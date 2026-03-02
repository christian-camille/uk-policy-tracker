from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_govuk_for_topic(self, topic_id: int):
    """Stub: GOV.UK ingestion for a topic. Implemented in Phase 4."""
    return {"status": "not_implemented", "topic_id": topic_id}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_parliament_for_topic(self, topic_id: int):
    """Stub: Parliament ingestion for a topic. Implemented in Phase 4."""
    return {"status": "not_implemented", "topic_id": topic_id}


@celery_app.task
def run_entity_matching(topic_id: int):
    """Stub: NLP entity matching for a topic. Implemented in Phase 5."""
    return {"status": "not_implemented", "topic_id": topic_id}


@celery_app.task
def rebuild_graph_projection():
    """Stub: rebuild gold graph projection. Implemented in Phase 6."""
    return {"status": "not_implemented"}
