import logging
from datetime import datetime

import httpx

from app.database import get_sync_session
from app.models.silver import Topic
from app.services.govuk import GovUkClientSync
from app.services.ingest import IngestService
from app.services.parliament import ParliamentClientSync
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_govuk_for_topic(self, topic_id: int, allow_private: bool = False):
    """Fetch GOV.UK search results for a topic, store in bronze, transform to silver."""
    with get_sync_session() as db:
        topic = db.get(Topic, topic_id)
        if not topic:
            return {"error": f"Topic {topic_id} not found"}

        if not topic.is_global and not allow_private:
            logger.info("Skipping private topic %d for scheduled GOV.UK ingest", topic_id)
            return {"topic_id": topic_id, "status": "skipped_private"}

        with httpx.Client(timeout=30) as http:
            client = GovUkClientSync(http)
            results = client.discover_for_topic(topic)

        ingest = IngestService(db)
        count = 0
        for result in results:
            try:
                ingest.upsert_govuk_content(result, source_query=topic.slug, topic_id=topic.id)
                count += 1
            except Exception:
                logger.exception("Failed to ingest GOV.UK item: %s", result.get("link"))

        topic.last_refreshed_at = datetime.utcnow()
        db.commit()

    logger.info("GOV.UK ingestion complete for topic %d: %d items", topic_id, count)
    return {"topic_id": topic_id, "items_ingested": count}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_parliament_for_topic(self, topic_id: int, allow_private: bool = False):
    """Fetch Parliament bills, questions, divisions for a topic."""
    with get_sync_session() as db:
        topic = db.get(Topic, topic_id)
        if not topic:
            return {"error": f"Topic {topic_id} not found"}

        if not topic.is_global and not allow_private:
            logger.info("Skipping private topic %d for scheduled Parliament ingest", topic_id)
            return {"topic_id": topic_id, "status": "skipped_private"}

        with httpx.Client(timeout=30) as http:
            client = ParliamentClientSync(http)
            results = client.discover_for_topic(topic)

        ingest = IngestService(db)
        counts = {"bills": 0, "questions": 0, "divisions": 0}

        for bill_data in results["bills"]:
            try:
                ingest.upsert_bill(bill_data, source_query=topic.slug)
                counts["bills"] += 1
            except Exception:
                logger.exception("Failed to ingest bill: %s", bill_data.get("billId"))

        for question_data in results["questions"]:
            try:
                ingest.upsert_question(question_data, source_query=topic.slug)
                counts["questions"] += 1
            except Exception:
                logger.exception("Failed to ingest question: %s", question_data.get("id"))

        for division_data in results["divisions"]:
            try:
                ingest.upsert_division(division_data, source_query=topic.slug)
                counts["divisions"] += 1
            except Exception:
                logger.exception(
                    "Failed to ingest division: %s", division_data.get("DivisionId")
                )

        db.commit()

    logger.info("Parliament ingestion complete for topic %d: %s", topic_id, counts)
    return {"topic_id": topic_id, **counts}


@celery_app.task
def create_activity_events(topic_id: int):
    """Create ActivityEvent rows from ingested silver data for a topic."""
    with get_sync_session() as db:
        ingest = IngestService(db)
        count = ingest.create_activity_events_for_topic(topic_id)
        db.commit()

    logger.info("Created %d activity events for topic %d", count, topic_id)
    return {"topic_id": topic_id, "events_created": count}


@celery_app.task
def run_entity_matching(topic_id: int):
    """Run spaCy NER on content items for a topic and resolve against silver tables."""
    from app.config import get_settings
    from app.nlp.extractor import EntityExtractor
    from app.services.matching import MatchingService

    settings = get_settings()

    with get_sync_session() as db:
        extractor = EntityExtractor(model_name=settings.SPACY_MODEL)
        service = MatchingService(db, extractor)
        service.load_patterns()
        count = service.match_content_items_for_topic(topic_id)
        db.commit()

    logger.info("Entity matching complete for topic %d: %d mentions", topic_id, count)
    return {"topic_id": topic_id, "mentions_created": count}


@celery_app.task
def rebuild_graph_projection():
    """Truncate and rebuild gold.graph_nodes + gold.graph_edges from silver tables."""
    from app.services.graph import GraphProjectionBuilder

    with get_sync_session() as db:
        builder = GraphProjectionBuilder(db)
        stats = builder.rebuild()
        db.commit()

    logger.info("Graph projection rebuilt: %s", stats)
    return stats
