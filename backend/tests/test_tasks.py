"""Tests for Celery task orchestration and individual tasks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestIngestTasks:
    """Test task functions can be called with mocked dependencies."""

    @patch("app.tasks.ingest.get_sync_session")
    @patch("app.tasks.ingest.GovUkClientSync")
    def test_ingest_govuk_topic_not_found(self, mock_client_cls, mock_session_ctx):
        from app.tasks.ingest import ingest_govuk_for_topic

        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        result = ingest_govuk_for_topic(topic_id=9999)
        assert result == {"error": "Topic 9999 not found"}

    @patch("app.tasks.ingest.get_sync_session")
    @patch("app.tasks.ingest.GovUkClientSync")
    def test_ingest_govuk_processes_results(self, mock_client_cls, mock_session_ctx):
        from app.tasks.ingest import ingest_govuk_for_topic

        mock_topic = MagicMock()
        mock_topic.id = 1
        mock_topic.slug = "test"
        mock_topic.search_queries = ["test"]
        mock_topic.is_global = True

        mock_session = MagicMock()
        mock_session.get.return_value = mock_topic

        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_http = MagicMock()
        mock_client = MagicMock()
        mock_client.discover_for_topic.return_value = [
            {"_id": "/doc/1", "link": "/doc/1", "title": "Doc 1"},
        ]
        mock_client_cls.return_value = mock_client

        with patch("app.tasks.ingest.httpx") as mock_httpx:
            mock_httpx.Client.return_value.__enter__ = MagicMock(return_value=mock_http)
            mock_httpx.Client.return_value.__exit__ = MagicMock(return_value=False)
            # Patch IngestService too
            with patch("app.tasks.ingest.IngestService") as mock_ingest_cls:
                mock_ingest = MagicMock()
                mock_ingest_cls.return_value = mock_ingest

                result = ingest_govuk_for_topic(topic_id=1)

        assert result["topic_id"] == 1
        assert result["items_ingested"] == 1

    @patch("app.tasks.ingest.get_sync_session")
    @patch("app.tasks.ingest.GovUkClientSync")
    def test_ingest_govuk_skips_private_topic_by_default(
        self, mock_client_cls, mock_session_ctx
    ):
        from app.tasks.ingest import ingest_govuk_for_topic

        mock_topic = MagicMock()
        mock_topic.id = 7
        mock_topic.is_global = False

        mock_session = MagicMock()
        mock_session.get.return_value = mock_topic
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        result = ingest_govuk_for_topic(topic_id=7)
        assert result == {"topic_id": 7, "status": "skipped_private"}
        mock_client_cls.assert_not_called()

    @patch("app.tasks.ingest.get_sync_session")
    def test_ingest_parliament_topic_not_found(self, mock_session_ctx):
        from app.tasks.ingest import ingest_parliament_for_topic

        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        result = ingest_parliament_for_topic(topic_id=9999)
        assert result == {"error": "Topic 9999 not found"}

    @patch("app.tasks.ingest.get_sync_session")
    @patch("app.tasks.ingest.ParliamentClientSync")
    def test_ingest_parliament_skips_private_topic_by_default(
        self, mock_client_cls, mock_session_ctx
    ):
        from app.tasks.ingest import ingest_parliament_for_topic

        mock_topic = MagicMock()
        mock_topic.id = 8
        mock_topic.is_global = False

        mock_session = MagicMock()
        mock_session.get.return_value = mock_topic
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        result = ingest_parliament_for_topic(topic_id=8)
        assert result == {"topic_id": 8, "status": "skipped_private"}
        mock_client_cls.assert_not_called()

    @patch("app.tasks.ingest.get_sync_session")
    def test_create_activity_events(self, mock_session_ctx):
        from app.tasks.ingest import create_activity_events

        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.tasks.ingest.IngestService") as mock_ingest_cls:
            mock_ingest = MagicMock()
            mock_ingest.create_activity_events_for_topic.return_value = 5
            mock_ingest_cls.return_value = mock_ingest

            result = create_activity_events(topic_id=1)

        assert result["topic_id"] == 1
        assert result["events_created"] == 5

    @patch("app.tasks.ingest.get_sync_session")
    def test_rebuild_graph_projection(self, mock_session_ctx):
        from app.tasks.ingest import rebuild_graph_projection

        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.services.graph.GraphProjectionBuilder") as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.rebuild.return_value = {"nodes": 10, "edges": 5}
            mock_builder_cls.return_value = mock_builder

            result = rebuild_graph_projection()

        assert result == {"nodes": 10, "edges": 5}


class TestPipelineTasks:
    """Test pipeline orchestration tasks."""

    @patch("app.tasks.pipeline.rebuild_graph_projection")
    @patch("app.tasks.pipeline.run_entity_matching")
    @patch("app.tasks.pipeline.create_activity_events")
    @patch("app.tasks.pipeline.ingest_parliament_for_topic")
    @patch("app.tasks.pipeline.ingest_govuk_for_topic")
    def test_refresh_single_topic_builds_pipeline(
        self, mock_govuk, mock_parl, mock_events, mock_match, mock_graph
    ):
        from app.tasks.pipeline import refresh_single_topic

        # Mock the Celery primitives
        mock_govuk.si = MagicMock()
        mock_parl.si = MagicMock()
        mock_events.si = MagicMock()
        mock_match.si = MagicMock()
        mock_graph.si = MagicMock()

        result = refresh_single_topic(topic_id=1)
        assert result["status"] == "pipeline_started"
        assert result["topic_id"] == 1
        mock_govuk.si.assert_called_once_with(1, True)
        mock_parl.si.assert_called_once_with(1, True)

    @patch("app.tasks.pipeline.get_sync_session")
    @patch("app.tasks.pipeline.rebuild_graph_projection")
    @patch("app.tasks.pipeline.run_entity_matching")
    @patch("app.tasks.pipeline.create_activity_events")
    @patch("app.tasks.pipeline.ingest_parliament_for_topic")
    @patch("app.tasks.pipeline.ingest_govuk_for_topic")
    def test_daily_refresh_no_topics(
        self, mock_govuk, mock_parl, mock_events, mock_match, mock_graph, mock_session_ctx
    ):
        from app.tasks.pipeline import daily_refresh_all_topics

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        result = daily_refresh_all_topics()
        assert result == {"status": "no_topics"}

    @patch("app.tasks.pipeline.get_sync_session")
    @patch("app.tasks.pipeline.rebuild_graph_projection")
    @patch("app.tasks.pipeline.run_entity_matching")
    @patch("app.tasks.pipeline.create_activity_events")
    @patch("app.tasks.pipeline.ingest_parliament_for_topic")
    @patch("app.tasks.pipeline.ingest_govuk_for_topic")
    def test_daily_refresh_uses_shared_topics_only(
        self, mock_govuk, mock_parl, mock_events, mock_match, mock_graph, mock_session_ctx
    ):
        from app.tasks.pipeline import daily_refresh_all_topics

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [(1,), (2,)]
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_govuk.si = MagicMock()
        mock_parl.si = MagicMock()
        mock_events.si = MagicMock()
        mock_match.si = MagicMock()
        mock_graph.si = MagicMock()

        result = daily_refresh_all_topics()

        assert result == {"status": "pipeline_started", "topics": 2}
        mock_govuk.si.assert_any_call(1, False)
        mock_govuk.si.assert_any_call(2, False)
        mock_parl.si.assert_any_call(1, False)
        mock_parl.si.assert_any_call(2, False)
