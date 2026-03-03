from __future__ import annotations

import logging
from dataclasses import dataclass

import spacy
from spacy.language import Language

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    text: str
    label: str  # PERSON, ORG, GPE, LAW, EVENT, etc.
    start_char: int
    end_char: int


class EntityExtractor:
    """Wraps spaCy NER to extract entities from GOV.UK content text."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.nlp: Language = spacy.load(model_name)
        self._ruler_added = False

    def extract(self, text: str) -> list[ExtractedEntity]:
        """Run NER on text and return entities of interest."""
        doc = self.nlp(text)
        entities: list[ExtractedEntity] = []
        seen: set[tuple[str, str]] = set()

        for ent in doc.ents:
            if ent.label_ not in ("PERSON", "ORG", "GPE", "LAW", "EVENT", "NORP"):
                continue
            # Deduplicate by (normalized text, label)
            key = (ent.text.strip().lower(), ent.label_)
            if key in seen:
                continue
            seen.add(key)

            entities.append(
                ExtractedEntity(
                    text=ent.text.strip(),
                    label=ent.label_,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                )
            )
        return entities

    def add_bill_patterns(self, bill_titles: list[str]) -> None:
        """
        Add EntityRuler patterns for known bill titles so spaCy
        recognises them even when the default model doesn't.
        """
        if self._ruler_added:
            # Remove existing ruler to rebuild with fresh patterns
            if self.nlp.has_pipe("entity_ruler"):
                self.nlp.remove_pipe("entity_ruler")

        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        patterns = [{"label": "LAW", "pattern": title} for title in bill_titles if title]
        ruler.add_patterns(patterns)
        self._ruler_added = True
        logger.info("Added %d bill title patterns to EntityRuler", len(patterns))

    def add_person_patterns(self, person_names: list[str]) -> None:
        """
        Add patterns for known MP/Lord names to improve recall.
        Appends to existing ruler if one exists.
        """
        if not self.nlp.has_pipe("entity_ruler"):
            self.nlp.add_pipe("entity_ruler", before="ner")

        ruler = self.nlp.get_pipe("entity_ruler")
        patterns = [{"label": "PERSON", "pattern": name} for name in person_names if name]
        ruler.add_patterns(patterns)
        logger.info("Added %d person name patterns to EntityRuler", len(patterns))
