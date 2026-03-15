import logging

from app.services.refresh import run_all_topic_refreshes, run_topic_refresh

logger = logging.getLogger(__name__)


def refresh_single_topic(topic_id: int):
    """On-demand refresh for a single topic using in-process execution."""
    result = run_topic_refresh(topic_id)
    return {"status": "completed", "topic_id": topic_id, "result": result}


def daily_refresh_all_topics():
    """Refresh all shared topics using in-process execution."""
    result = run_all_topic_refreshes()
    logger.info("Completed refresh for %d shared topics", result["topics"])
    return result
