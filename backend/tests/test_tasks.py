"""Tests for local refresh orchestration and ingest helper functions."""

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
    def test_ingest_govuk_continues_after_one_item_fails(
        self, mock_client_cls, mock_session_ctx
    ):
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
            {"_id": "/doc/2", "link": "/doc/2", "title": "Doc 2"},
        ]
        mock_client_cls.return_value = mock_client

        with patch("app.tasks.ingest.httpx") as mock_httpx:
            mock_httpx.Client.return_value.__enter__ = MagicMock(return_value=mock_http)
            mock_httpx.Client.return_value.__exit__ = MagicMock(return_value=False)
            with patch("app.tasks.ingest.IngestService") as mock_ingest_cls:
                mock_ingest = MagicMock()
                mock_ingest.upsert_govuk_content.side_effect = [
                    RuntimeError("bad row"),
                    None,
                ]
                mock_ingest_cls.return_value = mock_ingest

                result = ingest_govuk_for_topic(topic_id=1)

        assert result == {"topic_id": 1, "items_ingested": 1}
        assert mock_ingest.upsert_govuk_content.call_count == 2
        assert mock_session.begin_nested.call_count == 2
        mock_session.commit.assert_called_once()

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
    """Test local refresh orchestration wrappers."""

    @patch("app.tasks.pipeline.run_topic_refresh")
    def test_refresh_single_topic_runs_service(self, mock_run_topic_refresh):
        from app.tasks.pipeline import refresh_single_topic

        mock_run_topic_refresh.return_value = {"events": {"events_created": 3}}

        result = refresh_single_topic(topic_id=1)
        assert result["status"] == "completed"
        assert result["topic_id"] == 1
        assert result["result"]["events"]["events_created"] == 3
        mock_run_topic_refresh.assert_called_once_with(1)

    @patch("app.tasks.pipeline.run_all_topic_refreshes")
    def test_daily_refresh_no_topics(self, mock_run_all):
        from app.tasks.pipeline import daily_refresh_all_topics

        mock_run_all.return_value = {"status": "no_topics", "topics": 0, "results": []}

        result = daily_refresh_all_topics()
        assert result == {"status": "no_topics", "topics": 0, "results": []}
        mock_run_all.assert_called_once_with()

    @patch("app.tasks.pipeline.run_all_topic_refreshes")
    def test_daily_refresh_returns_completed_result(self, mock_run_all):
        from app.tasks.pipeline import daily_refresh_all_topics

        mock_run_all.return_value = {"status": "completed", "topics": 2, "results": []}

        result = daily_refresh_all_topics()

        assert result == {"status": "completed", "topics": 2, "results": []}
        mock_run_all.assert_called_once_with()
