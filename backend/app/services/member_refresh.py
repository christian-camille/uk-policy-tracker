import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import get_sync_session
from app.models.silver import Division, Person
from app.services.ingest import IngestService
from app.services.parliament import ParliamentClientSync

logger = logging.getLogger(__name__)

MAX_VOTING_PAGES = 10  # 10 pages * 20 per page = 200 votes max
VOTING_PAGE_SIZE = 20


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def run_member_refresh(parliament_id: int) -> dict:
    """Refresh profile and voting records for a single tracked member."""
    with httpx.Client(timeout=30) as http:
        client = ParliamentClientSync(http)

        # 1. Re-fetch member profile
        try:
            member_data = client.get_member(parliament_id)
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch member %d: %s", parliament_id, exc)
            return {"parliament_id": parliament_id, "error": str(exc)}

        # 2. Fetch voting records (paginated, capped)
        all_votes: list[dict] = []
        for page in range(MAX_VOTING_PAGES):
            try:
                data = client.get_member_voting(
                    parliament_id, house=1, skip=page * VOTING_PAGE_SIZE, take=VOTING_PAGE_SIZE
                )
            except httpx.HTTPError as exc:
                logger.warning(
                    "Failed to fetch voting page %d for member %d: %s",
                    page, parliament_id, exc,
                )
                break

            items = data.get("items", []) if isinstance(data, dict) else data
            if not items:
                break

            for item in items:
                # The Members voting endpoint wraps each record in 'value'
                vote_data = item.get("value", item) if isinstance(item, dict) else item
                all_votes.append(vote_data)

            if len(items) < VOTING_PAGE_SIZE:
                break

    # 3. Ingest into database
    with get_sync_session() as db:
        ingest = IngestService(db)

        # Upsert member profile
        person = ingest.upsert_member(member_data, source_query="mp_tracking")
        person.is_tracked = True
        person.last_refreshed_at = datetime.utcnow()
        db.flush()

        # Upsert divisions and votes
        vote_count = 0
        for vote_data in all_votes:
            try:
                # The Members voting endpoint uses "id" for division ID
                division_id_ext = vote_data.get("id")
                if not division_id_ext:
                    continue

                # Ensure division exists
                existing_div = db.execute(
                    select(Division).where(
                        Division.parliament_division_id == division_id_ext
                    )
                ).scalar_one_or_none()

                if not existing_div:
                    # Create a minimal division record from voting endpoint data
                    stmt = pg_insert(Division).values(
                        parliament_division_id=division_id_ext,
                        title=vote_data.get("title", "Unknown Division"),
                        date=_parse_datetime(vote_data.get("date")) or datetime.utcnow(),
                        house="Commons",
                        aye_count=vote_data.get("numberInFavour", 0),
                        no_count=vote_data.get("numberAgainst", 0),
                        number=vote_data.get("divisionNumber"),
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=["parliament_division_id"])
                    db.execute(stmt)
                    db.flush()

                    existing_div = db.execute(
                        select(Division).where(
                            Division.parliament_division_id == division_id_ext
                        )
                    ).scalar_one_or_none()

                if not existing_div:
                    continue

                # Determine vote direction from lobby flags
                in_aye = vote_data.get("inAffirmativeLobby", False)
                vote_direction = "aye" if in_aye else "no"

                ingest.upsert_division_vote(
                    division_id=existing_div.id,
                    person_id=person.id,
                    parliament_member_id=parliament_id,
                    vote=vote_direction,
                )
                vote_count += 1
            except Exception:
                logger.exception(
                    "Failed to ingest vote for member %d, division %s",
                    parliament_id,
                    vote_data.get("id"),
                )

        db.commit()

    logger.info(
        "Member refresh complete for %d: %d votes ingested", parliament_id, vote_count
    )
    return {"parliament_id": parliament_id, "votes_ingested": vote_count}


def run_all_member_refreshes() -> dict:
    """Refresh data for all tracked members."""
    with get_sync_session() as db:
        parliament_ids = [
            pid
            for (pid,) in db.query(Person.parliament_id).filter(
                Person.is_tracked.is_(True)
            )
        ]

    if not parliament_ids:
        return {"status": "no_tracked_members", "members": 0, "results": []}

    results = [
        {"parliament_id": pid, "result": run_member_refresh(pid)}
        for pid in parliament_ids
    ]
    return {"status": "completed", "members": len(results), "results": results}
