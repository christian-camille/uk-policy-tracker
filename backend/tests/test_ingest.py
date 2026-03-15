"""Tests for the IngestService — parsing raw API data into bronze/silver layers."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bronze import RawGovukItem, RawParliamentItem
from app.models.silver import (
    ActivityEvent,
    Bill,
    ContentItem,
    ContentItemOrganisation,
    ContentItemTopic,
    Division,
    Organisation,
    Person,
    WrittenQuestion,
)
from app.services.ingest import IngestService, _parse_datetime, _parse_date

from tests.conftest import make_bill, make_content_item, make_person, make_topic


# ── Datetime helpers ─────────────────────────────────────────────────


class TestParseDatetime:
    def test_iso_with_z(self):
        result = _parse_datetime("2024-01-15T12:00:00Z")
        assert result is not None
        assert result.year == 2024

    def test_iso_with_offset(self):
        result = _parse_datetime("2024-06-01T08:30:00+01:00")
        assert result is not None

    def test_none_input(self):
        assert _parse_datetime(None) is None

    def test_invalid_string(self):
        assert _parse_datetime("not-a-date") is None


class TestParseDate:
    def test_parses_to_date(self):
        result = _parse_date("2024-01-15T12:00:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_none_input(self):
        assert _parse_date(None) is None


# ── GOV.UK ingestion ─────────────────────────────────────────────────


class TestUpsertGovukContent:
    def test_content_id_columns_allow_long_path_identifiers(self):
        assert RawGovukItem.__table__.c.content_id.type.length == 512
        assert ContentItem.__table__.c.content_id.type.length == 512
        assert Organisation.__table__.c.acronym.type.length == 256

    def test_creates_bronze_and_silver_records(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "_id": "/government/publications/ai-regulation",
            "link": "/government/publications/ai-regulation",
            "title": "AI Regulation",
            "document_type": "policy_paper",
            "description": "Policy paper on AI regulation",
            "public_timestamp": "2024-03-15T10:00:00Z",
        }

        ci = service.upsert_govuk_content(raw, source_query="ai-policy")
        db_session.flush()

        assert ci.title == "AI Regulation"
        assert ci.content_id == "/government/publications/ai-regulation"
        assert ci.base_path == "/government/publications/ai-regulation"

        # Bronze record should exist
        bronze = db_session.execute(select(RawGovukItem)).scalar_one()
        assert bronze.base_path == "/government/publications/ai-regulation"

    def test_accepts_long_path_like_content_identifier(self, db_session: Session):
        service = IngestService(db_session)
        long_path = "/government/news/" + "cybersecurity-leaders-to-fortify-digital-defences-" * 2
        raw = {
            "_id": long_path,
            "link": long_path,
            "title": "Long GOV.UK Path",
            "document_type": "world_news_story",
        }

        ci = service.upsert_govuk_content(raw, source_query="cybersecurity")
        db_session.flush()

        bronze = db_session.execute(select(RawGovukItem)).scalar_one()
        assert ci.content_id == long_path
        assert bronze.content_id == long_path

    def test_upsert_is_idempotent(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "_id": "/doc/1",
            "link": "/doc/1",
            "title": "Version 1",
            "document_type": "guide",
        }
        service.upsert_govuk_content(raw, source_query="test")

        raw["title"] = "Version 2"
        ci = service.upsert_govuk_content(raw, source_query="test")
        db_session.flush()

        assert ci.title == "Version 2"
        # Should still be one record, not two
        count = db_session.execute(select(ContentItem)).scalars().all()
        assert len(count) == 1

    def test_links_to_topic(self, db_session: Session):
        topic = make_topic(db_session)
        service = IngestService(db_session)
        raw = {
            "_id": "/doc/linked",
            "link": "/doc/linked",
            "title": "Linked Doc",
            "document_type": "news_story",
        }
        service.upsert_govuk_content(raw, source_query="test", topic_id=topic.id)
        db_session.flush()

        link = db_session.execute(select(ContentItemTopic)).scalar_one()
        assert link.topic_id == topic.id

    def test_upserts_organisations(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "_id": "/doc/org-test",
            "link": "/doc/org-test",
            "title": "Org Test",
            "document_type": "notice",
            "organisations": [
                {
                    "content_id": "org-abc",
                    "title": "Home Office",
                    "acronym": "HO",
                    "slug": "home-office",
                }
            ],
        }
        service.upsert_govuk_content(raw, source_query="test")
        db_session.flush()

        org = db_session.execute(select(Organisation)).scalar_one()
        assert org.title == "Home Office"
        assert org.acronym == "HO"

        link = db_session.execute(select(ContentItemOrganisation)).scalar_one()
        assert link is not None

    def test_accepts_long_organisation_acronym_values(self, db_session: Session):
        service = IngestService(db_session)
        long_acronym = "The Traffic Commissioners for Great Britain"
        raw = {
            "_id": "/doc/long-org-acronym",
            "link": "/doc/long-org-acronym",
            "title": "Organisation Acronym Test",
            "document_type": "notice",
            "organisations": [
                {
                    "content_id": "org-long-acronym",
                    "title": "Traffic Commissioners",
                    "acronym": long_acronym,
                    "slug": "traffic-commissioners",
                }
            ],
        }

        service.upsert_govuk_content(raw, source_query="transport")
        db_session.flush()

        org = db_session.execute(select(Organisation)).scalar_one()
        assert org.acronym == long_acronym


# ── Parliament: Bills ────────────────────────────────────────────────


class TestUpsertBill:
    def test_creates_bill(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "billId": 100,
            "shortTitle": "Online Safety Bill",
            "currentHouse": "Commons",
            "originatingHouse": "Commons",
            "isAct": False,
            "isDefeated": False,
            "currentStage": {"description": "Report stage"},
            "lastUpdate": "2024-06-01T00:00:00Z",
        }
        bill = service.upsert_bill(raw, source_query="test")
        db_session.flush()

        assert bill.short_title == "Online Safety Bill"
        assert bill.current_stage == "Report stage"
        assert bill.parliament_bill_id == 100

    def test_upsert_bill_updates_existing(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "billId": 200,
            "shortTitle": "Old Title",
            "isAct": False,
            "isDefeated": False,
        }
        service.upsert_bill(raw, source_query="test")

        raw["shortTitle"] = "New Title"
        raw["isAct"] = True
        bill = service.upsert_bill(raw, source_query="test")
        db_session.flush()

        assert bill.short_title == "New Title"
        assert bill.is_act is True


# ── Parliament: Questions ────────────────────────────────────────────


class TestUpsertQuestion:
    def test_creates_question(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "id": 500,
            "uin": "12345",
            "heading": "Energy costs question",
            "questionText": "What is the government doing?",
            "house": 1,
            "dateTabled": "2024-03-01T00:00:00Z",
            "answeringBodyName": "DESNZ",
        }
        q = service.upsert_question(raw, source_query="test")
        db_session.flush()

        assert q.heading == "Energy costs question"
        assert q.house == "Commons"  # 1 -> Commons
        assert q.uin == "12345"

    def test_house_lords(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "id": 501,
            "uin": "HL-100",
            "heading": "Lords question",
            "house": 2,
        }
        q = service.upsert_question(raw, source_query="test")
        assert q.house == "Lords"

    def test_ensures_member_stub(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "id": 502,
            "uin": "12346",
            "heading": "Question with member",
            "house": 1,
            "askingMemberId": 9999,
        }
        service.upsert_question(raw, source_query="test")
        db_session.flush()

        person = db_session.execute(
            select(Person).where(Person.parliament_id == 9999)
        ).scalar_one()
        assert person.name_display == "Member #9999"


# ── Parliament: Divisions ────────────────────────────────────────────


class TestUpsertDivision:
    def test_creates_division(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "DivisionId": 300,
            "Title": "Motion on Climate Change",
            "Date": "2024-02-15T14:30:00Z",
            "AyeCount": 300,
            "NoCount": 200,
            "Number": 42,
        }
        div = service.upsert_division(raw, source_query="test")
        db_session.flush()

        assert div.title == "Motion on Climate Change"
        assert div.aye_count == 300
        assert div.no_count == 200


# ── Parliament: Members ──────────────────────────────────────────────


class TestUpsertMember:
    def test_creates_member(self, db_session: Session):
        service = IngestService(db_session)
        raw = {
            "id": 1234,
            "nameDisplayAs": "Keir Starmer",
            "nameListAs": "Starmer, Keir",
            "latestParty": {"name": "Labour"},
            "latestHouseMembership": {
                "house": 1,
                "membershipFrom": "Holborn and St Pancras",
                "membershipStatus": {"statusIsActive": True},
            },
            "thumbnailUrl": "https://example.com/photo.jpg",
        }
        person = service.upsert_member(raw, source_query="test")
        db_session.flush()

        assert person.name_display == "Keir Starmer"
        assert person.party == "Labour"
        assert person.house == "Commons"
        assert person.constituency == "Holborn and St Pancras"
        assert person.is_active is True


# ── Activity events ──────────────────────────────────────────────────


class TestCreateActivityEvents:
    def test_creates_events_from_content_items(self, db_session: Session):
        topic = make_topic(db_session)
        ci = make_content_item(db_session)
        db_session.add(ContentItemTopic(content_item_id=ci.id, topic_id=topic.id))
        db_session.flush()

        service = IngestService(db_session)
        count = service.create_activity_events_for_topic(topic.id)
        db_session.flush()

        assert count >= 1  # At least one event from the content item
        events = db_session.execute(select(ActivityEvent)).scalars().all()
        assert len(events) >= 1
        assert events[0].event_type == "govuk_publication"

    def test_idempotent_event_creation(self, db_session: Session):
        topic = make_topic(db_session)
        ci = make_content_item(db_session)
        db_session.add(ContentItemTopic(content_item_id=ci.id, topic_id=topic.id))
        db_session.flush()

        service = IngestService(db_session)
        count1 = service.create_activity_events_for_topic(topic.id)
        db_session.flush()
        count2 = service.create_activity_events_for_topic(topic.id)
        db_session.flush()

        assert count1 >= 1
        assert count2 == 0  # No new events created second time
