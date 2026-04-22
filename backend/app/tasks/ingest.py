import logging
from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

import httpx

from app.database import get_sync_session
from app.models.silver import Topic
from app.services.govuk import GovUkClientSync
from app.services.ingest import IngestService, TopicMatchProvenance
from app.services.parliament import ParliamentClientSync

logger = logging.getLogger(__name__)


def _run_isolated_ingest_step(
    db,
    *,
    item_label: str,
    item_identifier: str | int | None,
    operation: Callable[[], None],
) -> bool:
    """Run one ingest step inside a savepoint so later items can still proceed."""
    try:
        with db.begin_nested():
            operation()
    except Exception:
        logger.exception("Failed to ingest %s: %s", item_label, item_identifier)
        return False
    return True


def ingest_govuk_for_topic(
    topic_id: int,
    allow_private: bool = False,
    refresh_run_id: str | None = None,
):
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
            succeeded = _run_isolated_ingest_step(
                db,
                item_label="GOV.UK item",
                item_identifier=result.get("link") or result.get("_id"),
                operation=lambda result=result: ingest.upsert_govuk_content(
                    result["payload"],
                    source_query=topic.slug,
                    topic_id=topic.id,
                    provenance=TopicMatchProvenance(
                        match_method=result["match_method"],
                        matched_by_query=result.get("matched_by_query"),
                        matched_by_rule_group=result.get("matched_by_rule_group"),
                        refresh_run_id=refresh_run_id,
                    ),
                ),
            )
            if succeeded:
                count += 1

        topic.last_refreshed_at = datetime.utcnow()
        db.commit()

    logger.info("GOV.UK ingestion complete for topic %d: %d items", topic_id, count)
    return {"topic_id": topic_id, "items_ingested": count}


def ingest_parliament_for_topic(
    topic_id: int,
    allow_private: bool = False,
    refresh_run_id: str | None = None,
):
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
        counts = {"bills": 0, "members": 0, "questions": 0, "divisions": 0}

        for bill_data in results["bills"]:
            succeeded = _run_isolated_ingest_step(
                db,
                item_label="bill",
                item_identifier=bill_data["payload"].get("billId"),
                operation=lambda bill_data=bill_data: ingest.upsert_bill(
                    bill_data["payload"],
                    source_query=topic.slug,
                    topic_id=topic.id,
                    provenance=TopicMatchProvenance(
                        match_method=bill_data["match_method"],
                        matched_by_query=bill_data.get("matched_by_query"),
                        matched_by_rule_group=bill_data.get("matched_by_rule_group"),
                        refresh_run_id=refresh_run_id,
                    ),
                ),
            )
            if succeeded:
                counts["bills"] += 1

        for member_data in results["members"]:
            succeeded = _run_isolated_ingest_step(
                db,
                item_label="member",
                item_identifier=member_data.get("id"),
                operation=lambda member_data=member_data: ingest.upsert_member(
                    member_data,
                    source_query=topic.slug,
                ),
            )
            if succeeded:
                counts["members"] += 1

        for question_data in results["questions"]:
            succeeded = _run_isolated_ingest_step(
                db,
                item_label="question",
                item_identifier=question_data["payload"].get("id"),
                operation=lambda question_data=question_data: ingest.upsert_question(
                    question_data["payload"],
                    source_query=topic.slug,
                    topic_id=topic.id,
                    provenance=TopicMatchProvenance(
                        match_method=question_data["match_method"],
                        matched_by_query=question_data.get("matched_by_query"),
                        matched_by_rule_group=question_data.get("matched_by_rule_group"),
                        refresh_run_id=refresh_run_id,
                    ),
                ),
            )
            if succeeded:
                counts["questions"] += 1

        for division_data in results["divisions"]:
            succeeded = _run_isolated_ingest_step(
                db,
                item_label="division",
                item_identifier=division_data["payload"].get("DivisionId"),
                operation=lambda division_data=division_data: ingest.upsert_division(
                    division_data["payload"],
                    source_query=topic.slug,
                    topic_id=topic.id,
                    provenance=TopicMatchProvenance(
                        match_method=division_data["match_method"],
                        matched_by_query=division_data.get("matched_by_query"),
                        matched_by_rule_group=division_data.get("matched_by_rule_group"),
                        refresh_run_id=refresh_run_id,
                    ),
                ),
            )
            if succeeded:
                counts["divisions"] += 1

        db.commit()

    logger.info("Parliament ingestion complete for topic %d: %s", topic_id, counts)
    return {"topic_id": topic_id, **counts}


def create_activity_events(topic_id: int):
    """Create ActivityEvent rows from ingested silver data for a topic."""
    with get_sync_session() as db:
        ingest = IngestService(db)
        count = ingest.create_activity_events_for_topic(topic_id)
        db.commit()

    logger.info("Created %d activity events for topic %d", count, topic_id)
    return {"topic_id": topic_id, "events_created": count}


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


def rebuild_graph_projection():
    """Truncate and rebuild gold.graph_nodes + gold.graph_edges from silver tables."""
    from app.services.graph import GraphProjectionBuilder

    with get_sync_session() as db:
        builder = GraphProjectionBuilder(db)
        stats = builder.rebuild()
        db.commit()

    logger.info("Graph projection rebuilt: %s", stats)
    return stats


def generate_refresh_run_id() -> str:
    return uuid4().hex
