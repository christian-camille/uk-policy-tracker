from __future__ import annotations

import logging

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.silver import (
    Bill,
    ContentItem,
    ContentItemTopic,
    EntityMention,
    Organisation,
    Person,
)
from app.nlp.extractor import EntityExtractor, ExtractedEntity

logger = logging.getLogger(__name__)


class MatchingService:
    """
    Resolves NLP-extracted entities from GOV.UK content against
    Parliament entity tables in the silver layer.
    Uses synchronous sessions for local refresh execution.
    """

    def __init__(self, db: Session, extractor: EntityExtractor):
        self.db = db
        self.extractor = extractor

    def load_patterns(self) -> None:
        """Load known bill titles and person names into the extractor's EntityRuler."""
        bill_titles = [
            row[0]
            for row in self.db.execute(select(Bill.short_title)).all()
            if row[0]
        ]
        if bill_titles:
            self.extractor.add_bill_patterns(bill_titles)

        person_names = [
            row[0]
            for row in self.db.execute(select(Person.name_display)).all()
            if row[0]
        ]
        if person_names:
            self.extractor.add_person_patterns(person_names)

    def match_content_items_for_topic(self, topic_id: int) -> int:
        """
        Run entity extraction on all content items linked to a topic,
        resolve matches against silver tables, and store as EntityMention rows.
        Returns count of new mentions created.
        """
        content_items = (
            self.db.execute(
                select(ContentItem)
                .join(
                    ContentItemTopic,
                    ContentItemTopic.content_item_id == ContentItem.id,
                )
                .where(ContentItemTopic.topic_id == topic_id)
            )
            .scalars()
            .all()
        )

        total_mentions = 0
        for ci in content_items:
            mentions = self._match_content_item(ci)
            total_mentions += mentions

        self.db.flush()
        logger.info(
            "Entity matching for topic %d: processed %d content items, %d new mentions",
            topic_id,
            len(content_items),
            total_mentions,
        )
        return total_mentions

    def _match_content_item(self, content_item: ContentItem) -> int:
        """Extract entities from title + description, resolve and store matches."""
        text = content_item.title or ""
        if content_item.description:
            text = f"{text}. {content_item.description}"

        if not text.strip():
            return 0

        extracted = self.extractor.extract(text)
        count = 0

        for ent in extracted:
            match = self._resolve_entity(ent)
            if match:
                entity_type, entity_id, confidence = match
                created = self._store_mention(
                    content_item_id=content_item.id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    mention_text=ent.text,
                    confidence=confidence,
                )
                if created:
                    count += 1

        return count

    def _resolve_entity(
        self, ent: ExtractedEntity
    ) -> tuple[str, int, float] | None:
        """
        Attempt to match an extracted entity to a silver table record.
        Returns (entity_type, entity_id, confidence) or None.
        """
        if ent.label == "PERSON":
            return self._resolve_person(ent.text)
        elif ent.label == "LAW":
            return self._resolve_bill(ent.text)
        elif ent.label == "ORG":
            return self._resolve_organisation(ent.text)
        return None

    def _resolve_person(self, name_text: str) -> tuple[str, int, float] | None:
        """
        Match an extracted person name to silver.persons.
        Strategy: exact match first, then pg_trgm similarity.
        """
        # 1. Exact match (case-insensitive)
        person = self.db.execute(
            select(Person).where(func.lower(Person.name_display) == name_text.lower())
        ).scalar_one_or_none()

        if person:
            return ("person", person.id, 1.0)

        # 2. Trigram similarity (requires pg_trgm extension)
        try:
            similarity = func.similarity(Person.name_display, name_text)
            result = self.db.execute(
                select(Person, similarity.label("sim"))
                .where(similarity > 0.4)
                .order_by(desc("sim"))
                .limit(1)
            ).first()

            if result and result.sim >= 0.6:
                return ("person", result.Person.id, float(result.sim))
        except Exception:
            # pg_trgm may not be available in test environments
            logger.debug("Trigram similarity search failed for %r", name_text)

        return None

    def _resolve_bill(self, title_text: str) -> tuple[str, int, float] | None:
        """Match an extracted bill/law reference against silver.bills."""
        # 1. Exact title match
        bill = self.db.execute(
            select(Bill).where(func.lower(Bill.short_title) == title_text.lower())
        ).scalar_one_or_none()

        if bill:
            return ("bill", bill.id, 1.0)

        # 2. Substring match (bill title contained in extracted text or vice versa)
        bill = self.db.execute(
            select(Bill).where(
                or_(
                    func.lower(Bill.short_title).contains(title_text.lower()),
                    func.lower(title_text).op("LIKE")(
                        func.concat("%", func.lower(Bill.short_title), "%")
                    ),
                )
            )
        ).scalar_one_or_none()

        if bill:
            return ("bill", bill.id, 0.7)

        # 3. Trigram similarity
        try:
            similarity = func.similarity(Bill.short_title, title_text)
            result = self.db.execute(
                select(Bill, similarity.label("sim"))
                .where(similarity > 0.4)
                .order_by(desc("sim"))
                .limit(1)
            ).first()

            if result and result.sim >= 0.6:
                return ("bill", result.Bill.id, float(result.sim))
        except Exception:
            logger.debug("Trigram similarity search failed for bill %r", title_text)

        return None

    def _resolve_organisation(
        self, org_text: str
    ) -> tuple[str, int, float] | None:
        """Match by title or acronym."""
        org = self.db.execute(
            select(Organisation).where(
                or_(
                    func.lower(Organisation.title) == org_text.lower(),
                    func.lower(Organisation.acronym) == org_text.lower(),
                )
            )
        ).scalar_one_or_none()

        if org:
            return ("organisation", org.id, 1.0)

        return None

    def _store_mention(
        self,
        content_item_id: int,
        entity_type: str,
        entity_id: int,
        mention_text: str,
        confidence: float,
    ) -> bool:
        """Store an EntityMention if it doesn't already exist. Returns True if created."""
        existing = self.db.execute(
            select(EntityMention).where(
                EntityMention.content_item_id == content_item_id,
                EntityMention.mentioned_entity_type == entity_type,
                EntityMention.mentioned_entity_id == entity_id,
            )
        ).scalar_one_or_none()

        if existing:
            return False

        self.db.add(
            EntityMention(
                content_item_id=content_item_id,
                mentioned_entity_type=entity_type,
                mentioned_entity_id=entity_id,
                mention_text=mention_text,
                confidence=confidence,
            )
        )
        return True
