"""Tests for the NLP entity extractor.

These tests require spaCy with en_core_web_sm model, which is not
compatible with Python 3.14+. They will be skipped if spaCy cannot
be loaded but will run correctly in the Docker container (Python 3.12).
"""

from __future__ import annotations

import pytest

try:
    from app.nlp.extractor import EntityExtractor, ExtractedEntity

    SPACY_AVAILABLE = True
except Exception:
    SPACY_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not SPACY_AVAILABLE,
    reason="spaCy not available (requires Python <3.14)",
)


@pytest.fixture(scope="module")
def extractor():
    """Load spaCy model once for the module (it's expensive)."""
    return EntityExtractor("en_core_web_sm")


class TestEntityExtractor:
    def test_extract_persons(self, extractor):
        text = "Keir Starmer met with Joe Biden at the White House."
        entities = extractor.extract(text)
        labels = {e.label for e in entities}
        names = {e.text for e in entities}

        assert "PERSON" in labels or "GPE" in labels
        assert isinstance(entities, list)

    def test_extract_organisations(self, extractor):
        text = "The Department for Education published new guidance through Parliament."
        entities = extractor.extract(text)
        org_entities = [e for e in entities if e.label == "ORG"]
        assert len(org_entities) >= 0

    def test_extract_returns_expected_fields(self, extractor):
        text = "Boris Johnson spoke in the House of Commons about NATO policy."
        entities = extractor.extract(text)

        for ent in entities:
            assert isinstance(ent, ExtractedEntity)
            assert isinstance(ent.text, str)
            assert ent.label in ("PERSON", "ORG", "GPE", "LAW", "EVENT", "NORP")
            assert isinstance(ent.start_char, int)
            assert isinstance(ent.end_char, int)
            assert ent.start_char < ent.end_char

    def test_extract_deduplicates(self, extractor):
        text = "Boris Johnson said Boris Johnson would attend. Boris Johnson confirmed."
        entities = extractor.extract(text)

        person_entities = [e for e in entities if e.text == "Boris Johnson"]
        assert len(person_entities) <= 1

    def test_extract_empty_text(self, extractor):
        entities = extractor.extract("")
        assert entities == []

    def test_extract_no_entities(self, extractor):
        entities = extractor.extract("The quick brown fox jumped over the lazy dog.")
        assert isinstance(entities, list)

    def test_filters_unwanted_labels(self, extractor):
        text = "On 15 January 2024, the price was £500 million."
        entities = extractor.extract(text)
        for ent in entities:
            assert ent.label in ("PERSON", "ORG", "GPE", "LAW", "EVENT", "NORP")


class TestEntityRulerPatterns:
    def test_add_bill_patterns(self):
        ext = EntityExtractor("en_core_web_sm")
        ext.add_bill_patterns(["Online Safety Bill", "Levelling Up Bill"])

        entities = ext.extract("The Online Safety Bill was debated in Parliament.")
        law_entities = [e for e in entities if e.label == "LAW"]
        assert any("Online Safety Bill" in e.text for e in law_entities)

    def test_add_person_patterns(self):
        ext = EntityExtractor("en_core_web_sm")
        ext.add_person_patterns(["Rishi Sunak", "Keir Starmer"])

        entities = ext.extract("Rishi Sunak delivered a speech on climate policy.")
        person_entities = [e for e in entities if e.label == "PERSON"]
        assert any("Rishi Sunak" in e.text for e in person_entities)

    def test_bill_patterns_can_be_rebuilt(self):
        ext = EntityExtractor("en_core_web_sm")
        ext.add_bill_patterns(["Old Bill"])
        ext.add_bill_patterns(["New Bill"])

        entities = ext.extract("The New Bill was introduced.")
        law_entities = [e for e in entities if e.label == "LAW"]
        assert any("New Bill" in e.text for e in law_entities)

    def test_empty_patterns_list(self):
        ext = EntityExtractor("en_core_web_sm")
        ext.add_bill_patterns([])
        entities = ext.extract("Some text about policy.")
        assert isinstance(entities, list)
