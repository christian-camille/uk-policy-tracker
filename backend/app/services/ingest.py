from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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

logger = logging.getLogger(__name__)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO datetime string, returning None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_date(value: str | None):
    """Parse an ISO date or datetime string to a date object."""
    dt = _parse_datetime(value)
    return dt.date() if dt else None


class IngestService:
    """
    Transforms raw API responses into bronze and silver layer tables.
    Uses synchronous sessions for local refresh execution.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── GOV.UK ────────────────────────────────────────────────────────────

    def upsert_govuk_content(
        self, raw_json: dict, source_query: str, topic_id: int | None = None
    ) -> ContentItem:
        """Store raw JSON in bronze, parse into silver.content_items."""
        link = raw_json.get("link", "")
        base_path = link if link.startswith("/") else f"/{link}"

        # Bronze upsert
        raw_item = self._upsert_raw_govuk(base_path, raw_json, source_query)

        # Silver upsert
        # Search results use `_id` as an opaque ID; Content API uses `content_id`.
        # Use `_id` from search results as the content_id field.
        content_id = raw_json.get("content_id") or raw_json.get("_id") or base_path
        public_updated_at = _parse_datetime(
            raw_json.get("public_timestamp") or raw_json.get("public_updated_at")
        )

        stmt = pg_insert(ContentItem).values(
            content_id=content_id,
            base_path=base_path,
            title=raw_json.get("title", "Untitled"),
            document_type=raw_json.get("document_type", "unknown"),
            description=raw_json.get("description"),
            public_updated_at=public_updated_at,
            govuk_url=f"https://www.gov.uk{base_path}",
            raw_item_id=raw_item.id,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["content_id"],
            set_={
                "title": stmt.excluded.title,
                "document_type": stmt.excluded.document_type,
                "description": stmt.excluded.description,
                "public_updated_at": stmt.excluded.public_updated_at,
                "raw_item_id": stmt.excluded.raw_item_id,
            },
        )
        self.db.execute(stmt)
        self.db.flush()

        # Retrieve the content item
        content_item = self.db.execute(
            select(ContentItem).where(ContentItem.content_id == content_id)
        ).scalar_one()

        # Upsert organisations from search result
        orgs = raw_json.get("organisations", [])
        for org_data in orgs:
            org = self._upsert_organisation(org_data)
            if org:
                self._link_content_organisation(content_item.id, org.id)

        # Link to topic
        if topic_id:
            self._link_content_topic(content_item.id, topic_id)

        return content_item

    def _upsert_raw_govuk(
        self, base_path: str, raw_json: dict, source_query: str
    ) -> RawGovukItem:
        stmt = pg_insert(RawGovukItem).values(
            base_path=base_path,
            content_id=raw_json.get("content_id") or raw_json.get("_id"),
            raw_json=raw_json,
            http_status=200,
            source_query=source_query,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["base_path"],
            set_={
                "raw_json": stmt.excluded.raw_json,
                "fetched_at": datetime.utcnow(),
                "source_query": stmt.excluded.source_query,
            },
        )
        self.db.execute(stmt)
        self.db.flush()

        return self.db.execute(
            select(RawGovukItem).where(RawGovukItem.base_path == base_path)
        ).scalar_one()

    def _upsert_organisation(self, org_data: dict) -> Organisation | None:
        """Upsert an organisation from GOV.UK search result org objects."""
        org_content_id = org_data.get("content_id")
        if not org_content_id:
            return None

        stmt = pg_insert(Organisation).values(
            content_id=org_content_id,
            title=org_data.get("title", "Unknown"),
            acronym=org_data.get("acronym"),
            slug=org_data.get("slug", org_content_id),
            state=org_data.get("organisation_state", "live"),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["content_id"],
            set_={
                "title": stmt.excluded.title,
                "acronym": stmt.excluded.acronym,
                "state": stmt.excluded.state,
            },
        )
        self.db.execute(stmt)
        self.db.flush()

        return self.db.execute(
            select(Organisation).where(Organisation.content_id == org_content_id)
        ).scalar_one_or_none()

    def _link_content_organisation(
        self, content_item_id: int, organisation_id: int
    ) -> None:
        existing = self.db.execute(
            select(ContentItemOrganisation).where(
                ContentItemOrganisation.content_item_id == content_item_id,
                ContentItemOrganisation.organisation_id == organisation_id,
            )
        ).scalar_one_or_none()
        if not existing:
            self.db.add(
                ContentItemOrganisation(
                    content_item_id=content_item_id,
                    organisation_id=organisation_id,
                )
            )

    def _link_content_topic(self, content_item_id: int, topic_id: int) -> None:
        existing = self.db.execute(
            select(ContentItemTopic).where(
                ContentItemTopic.content_item_id == content_item_id,
                ContentItemTopic.topic_id == topic_id,
            )
        ).scalar_one_or_none()
        if not existing:
            self.db.add(
                ContentItemTopic(
                    content_item_id=content_item_id,
                    topic_id=topic_id,
                )
            )

    # ── Parliament: Bills ─────────────────────────────────────────────────

    def upsert_bill(self, raw_json: dict, source_query: str) -> Bill:
        """Store raw JSON in bronze, parse into silver.bills."""
        bill_id = raw_json["billId"]

        # Bronze
        self._upsert_raw_parliament("bills", str(bill_id), raw_json, source_query)

        # Silver
        current_stage_desc = None
        current_stage = raw_json.get("currentStage")
        if isinstance(current_stage, dict):
            current_stage_desc = current_stage.get("description")

        stmt = pg_insert(Bill).values(
            parliament_bill_id=bill_id,
            short_title=raw_json.get("shortTitle", "Untitled"),
            current_house=raw_json.get("currentHouse"),
            originating_house=raw_json.get("originatingHouse"),
            last_update=_parse_datetime(raw_json.get("lastUpdate")),
            is_act=raw_json.get("isAct", False),
            is_defeated=raw_json.get("isDefeated", False),
            current_stage=current_stage_desc,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["parliament_bill_id"],
            set_={
                "short_title": stmt.excluded.short_title,
                "current_house": stmt.excluded.current_house,
                "last_update": stmt.excluded.last_update,
                "is_act": stmt.excluded.is_act,
                "is_defeated": stmt.excluded.is_defeated,
                "current_stage": stmt.excluded.current_stage,
            },
        )
        self.db.execute(stmt)
        self.db.flush()

        return self.db.execute(
            select(Bill).where(Bill.parliament_bill_id == bill_id)
        ).scalar_one()

    # ── Parliament: Questions ─────────────────────────────────────────────

    def upsert_question(self, raw_json: dict, source_query: str) -> WrittenQuestion:
        """Store raw JSON in bronze, parse into silver.written_questions."""
        question_id = raw_json["id"]

        # Bronze
        self._upsert_raw_parliament(
            "questions", str(question_id), raw_json, source_query
        )

        # Upsert asking member if present
        asking_member_id = raw_json.get("askingMemberId")
        if asking_member_id:
            self._ensure_member_stub(asking_member_id)

        # Determine house: API returns int (1=Commons, 2=Lords) or string
        house_raw = raw_json.get("house", "")
        if isinstance(house_raw, int):
            house = "Commons" if house_raw == 1 else "Lords"
        else:
            house = str(house_raw) if house_raw else "Commons"

        # Silver
        stmt = pg_insert(WrittenQuestion).values(
            parliament_question_id=question_id,
            uin=raw_json.get("uin", ""),
            heading=raw_json.get("heading", "Untitled"),
            question_text=raw_json.get("questionText"),
            house=house,
            date_tabled=_parse_date(raw_json.get("dateTabled")),
            date_answered=_parse_date(raw_json.get("dateAnswered")),
            asking_member_id=asking_member_id,
            answering_body=raw_json.get("answeringBodyName"),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["parliament_question_id"],
            set_={
                "heading": stmt.excluded.heading,
                "question_text": stmt.excluded.question_text,
                "date_answered": stmt.excluded.date_answered,
                "answering_body": stmt.excluded.answering_body,
            },
        )
        self.db.execute(stmt)
        self.db.flush()

        return self.db.execute(
            select(WrittenQuestion).where(
                WrittenQuestion.parliament_question_id == question_id
            )
        ).scalar_one()

    # ── Parliament: Divisions ─────────────────────────────────────────────

    def upsert_division(self, raw_json: dict, source_query: str) -> Division:
        """Store raw JSON in bronze, parse into silver.divisions."""
        division_id = raw_json["DivisionId"]

        # Bronze
        self._upsert_raw_parliament(
            "divisions", str(division_id), raw_json, source_query
        )

        # Silver
        stmt = pg_insert(Division).values(
            parliament_division_id=division_id,
            title=raw_json.get("Title", "Untitled"),
            date=_parse_datetime(raw_json.get("Date")) or datetime.utcnow(),
            house="Commons",  # Commons Votes API only covers Commons
            aye_count=raw_json.get("AyeCount", 0),
            no_count=raw_json.get("NoCount", 0),
            number=raw_json.get("Number"),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["parliament_division_id"],
            set_={
                "title": stmt.excluded.title,
                "aye_count": stmt.excluded.aye_count,
                "no_count": stmt.excluded.no_count,
            },
        )
        self.db.execute(stmt)
        self.db.flush()

        return self.db.execute(
            select(Division).where(Division.parliament_division_id == division_id)
        ).scalar_one()

    # ── Parliament: Members ───────────────────────────────────────────────

    def upsert_member(self, raw_json: dict, source_query: str) -> Person:
        """
        Upsert a member from the Members API response.
        `raw_json` should be the `value` object inside each search result item.
        """
        member_id = raw_json["id"]

        # Bronze
        self._upsert_raw_parliament("members", str(member_id), raw_json, source_query)

        # Parse party and house
        party_name = None
        latest_party = raw_json.get("latestParty")
        if isinstance(latest_party, dict):
            party_name = latest_party.get("name")

        house_name = None
        constituency = None
        is_active = True
        house_membership = raw_json.get("latestHouseMembership")
        if isinstance(house_membership, dict):
            house_int = house_membership.get("house")
            if house_int == 1:
                house_name = "Commons"
            elif house_int == 2:
                house_name = "Lords"
            constituency = house_membership.get("membershipFrom")
            membership_status = house_membership.get("membershipStatus")
            if isinstance(membership_status, dict):
                is_active = membership_status.get("statusIsActive", True)

        # Silver
        stmt = pg_insert(Person).values(
            parliament_id=member_id,
            name_display=raw_json.get("nameDisplayAs", "Unknown"),
            name_list=raw_json.get("nameListAs"),
            party=party_name,
            house=house_name,
            constituency=constituency,
            thumbnail_url=raw_json.get("thumbnailUrl"),
            is_active=is_active,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["parliament_id"],
            set_={
                "name_display": stmt.excluded.name_display,
                "name_list": stmt.excluded.name_list,
                "party": stmt.excluded.party,
                "house": stmt.excluded.house,
                "constituency": stmt.excluded.constituency,
                "thumbnail_url": stmt.excluded.thumbnail_url,
                "is_active": stmt.excluded.is_active,
            },
        )
        self.db.execute(stmt)
        self.db.flush()

        return self.db.execute(
            select(Person).where(Person.parliament_id == member_id)
        ).scalar_one()

    def _ensure_member_stub(self, parliament_id: int) -> None:
        """Create a minimal Person stub if we only have the ID (from a question)."""
        existing = self.db.execute(
            select(Person).where(Person.parliament_id == parliament_id)
        ).scalar_one_or_none()
        if not existing:
            self.db.add(
                Person(
                    parliament_id=parliament_id,
                    name_display=f"Member #{parliament_id}",
                    is_active=True,
                )
            )
            self.db.flush()

    # ── Bronze helper ─────────────────────────────────────────────────────

    def _upsert_raw_parliament(
        self,
        source_api: str,
        external_id: str,
        raw_json: dict,
        source_query: str,
    ) -> None:
        stmt = pg_insert(RawParliamentItem).values(
            source_api=source_api,
            external_id=external_id,
            raw_json=raw_json,
            source_query=source_query,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_parliament_source_id",
            set_={
                "raw_json": stmt.excluded.raw_json,
                "fetched_at": datetime.utcnow(),
                "source_query": stmt.excluded.source_query,
            },
        )
        self.db.execute(stmt)

    # ── Activity events ───────────────────────────────────────────────────

    def create_activity_events_for_topic(self, topic_id: int) -> int:
        """
        Scan silver tables for entities linked to this topic and create
        ActivityEvent rows for any that don't already have one.
        Returns the number of new events created.
        """
        count = 0

        # GOV.UK content items linked to this topic
        content_items = self.db.execute(
            select(ContentItem)
            .join(
                ContentItemTopic,
                ContentItemTopic.content_item_id == ContentItem.id,
            )
            .where(ContentItemTopic.topic_id == topic_id)
        ).scalars().all()

        for ci in content_items:
            count += self._ensure_activity_event(
                event_type="govuk_publication",
                event_date=ci.public_updated_at or ci.first_seen_at,
                title=ci.title,
                summary=ci.description,
                source_url=ci.govuk_url,
                source_entity_type="content_item",
                source_entity_id=ci.id,
                topic_id=topic_id,
            )

        # Bills — all bills ingested under this query are linked to the topic
        bills = self.db.execute(select(Bill)).scalars().all()
        for bill in bills:
            count += self._ensure_activity_event(
                event_type="bill_stage",
                event_date=bill.last_update or datetime.utcnow(),
                title=bill.short_title,
                summary=f"Stage: {bill.current_stage or 'Unknown'} | House: {bill.current_house or 'Unknown'}",
                source_url=None,
                source_entity_type="bill",
                source_entity_id=bill.id,
                topic_id=topic_id,
            )

        # Written questions
        questions = self.db.execute(select(WrittenQuestion)).scalars().all()
        for q in questions:
            event_type = "question_answered" if q.date_answered else "question_tabled"
            event_date = q.date_answered or q.date_tabled
            if event_date:
                event_dt = datetime.combine(event_date, datetime.min.time())
            else:
                event_dt = datetime.utcnow()

            count += self._ensure_activity_event(
                event_type=event_type,
                event_date=event_dt,
                title=q.heading,
                summary=q.answering_body,
                source_url=None,
                source_entity_type="question",
                source_entity_id=q.id,
                topic_id=topic_id,
            )

        # Divisions
        divisions = self.db.execute(select(Division)).scalars().all()
        for div in divisions:
            count += self._ensure_activity_event(
                event_type="division_held",
                event_date=div.date,
                title=div.title,
                summary=f"Ayes: {div.aye_count}, Noes: {div.no_count}",
                source_url=None,
                source_entity_type="division",
                source_entity_id=div.id,
                topic_id=topic_id,
            )

        self.db.flush()
        logger.info(
            "Created %d new activity events for topic_id=%d", count, topic_id
        )
        return count

    def _ensure_activity_event(
        self,
        event_type: str,
        event_date: datetime,
        title: str,
        summary: str | None,
        source_url: str | None,
        source_entity_type: str,
        source_entity_id: int,
        topic_id: int,
    ) -> int:
        """Create an ActivityEvent if one doesn't already exist. Returns 1 if created, 0 if skipped."""
        existing = self.db.execute(
            select(ActivityEvent).where(
                ActivityEvent.source_entity_type == source_entity_type,
                ActivityEvent.source_entity_id == source_entity_id,
                ActivityEvent.topic_id == topic_id,
            )
        ).scalar_one_or_none()

        if existing:
            return 0

        self.db.add(
            ActivityEvent(
                event_type=event_type,
                event_date=event_date,
                title=title,
                summary=summary,
                source_url=source_url,
                source_entity_type=source_entity_type,
                source_entity_id=source_entity_id,
                topic_id=topic_id,
            )
        )
        return 1
