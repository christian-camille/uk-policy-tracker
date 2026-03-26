"""Parse Commons division titles into structured components."""

import re

# Matches "Bill" optionally followed by "(Lords)" or "(HL)"
_BILL_RE = re.compile(
    r"^(.+?\bBill(?:\s*\((?:Lords|HL)\))?)\s*(.*)",
    re.IGNORECASE,
)

_OPPOSITION_DAY_RE = re.compile(
    r"^Opposition\s+Day\s*[\u2014\u2013\-:]\s*(.+)",
    re.IGNORECASE,
)


def parse_division_title(title: str) -> dict:
    """Parse a Commons division title into structured components.

    Returns dict with keys:
      bill_name  - e.g. "Finance Bill" or None
      stage      - e.g. "Committee" or None
      detail     - e.g. "Amendment 19" or None
      category   - "bill", "opposition_day", "motion", or "other"
    """
    if not title:
        return {"bill_name": None, "stage": None, "detail": None, "category": "other"}

    # Check for bill pattern
    m = _BILL_RE.match(title)
    if m:
        bill_name = m.group(1).strip()
        remainder = m.group(2).strip()

        stage = None
        detail = None

        if remainder:
            # Remainder may be "Committee: Amendment 19" or ": Third Reading" or "Third Reading"
            remainder = remainder.lstrip(":").strip()
            if ":" in remainder:
                stage, detail = remainder.split(":", 1)
                stage = stage.strip() or None
                detail = detail.strip() or None
            else:
                stage = remainder or None

        return {
            "bill_name": bill_name,
            "stage": stage,
            "detail": detail,
            "category": "bill",
        }

    # Check for Opposition Day pattern
    m = _OPPOSITION_DAY_RE.match(title)
    if m:
        return {
            "bill_name": None,
            "stage": None,
            "detail": m.group(1).strip(),
            "category": "opposition_day",
        }

    # Check for motion pattern  ("Subject: Motion" or "Subject: verb...")
    if ":" in title:
        return {
            "bill_name": None,
            "stage": None,
            "detail": title,
            "category": "motion",
        }

    return {"bill_name": None, "stage": None, "detail": None, "category": "other"}
