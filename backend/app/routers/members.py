import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.bronze import RawParliamentItem
from app.models.silver import Bill, Division, DivisionVote, Person, WrittenQuestion
from app.services.division_title_parser import parse_division_title
from app.schemas.members import (
    MemberQuestionRecord,
    MemberQuestionsResponse,
    MemberSearchResponse,
    MemberSearchResult,
    MemberVoteRecord,
    MemberVotesResponse,
    TrackedMemberListResponse,
    TrackedMemberSummary,
)
from app.services.member_refresh import run_all_member_refreshes, run_member_refresh
from app.services.parliament import DIVISIONS_API, MEMBERS_API, build_written_question_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/members", tags=["members"])


def _extract_member_search_value(item: dict) -> dict:
    value = item.get("value", item)
    return value if isinstance(value, dict) else {}


def _extract_member_search_id(item: dict) -> int | None:
    value = _extract_member_search_value(item)
    mid = value.get("id")
    return mid if isinstance(mid, int) else None


def _build_member_search_result(
    item: dict,
    tracked_ids: set[int],
    match_types: set[str],
) -> MemberSearchResult | None:
    value = _extract_member_search_value(item)
    mid = _extract_member_search_id(item)
    if mid is None:
        return None

    party_name = None
    latest_party = value.get("latestParty")
    if isinstance(latest_party, dict):
        party_name = latest_party.get("name")

    house_name = None
    constituency = None
    is_active = True
    house_membership = value.get("latestHouseMembership")
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

    return MemberSearchResult(
        parliament_id=mid,
        name_display=value.get("nameDisplayAs", "Unknown"),
        party=party_name,
        house=house_name,
        constituency=constituency,
        thumbnail_url=value.get("thumbnailUrl"),
        is_active=is_active,
        is_tracked=mid in tracked_ids,
        match_types=sorted(match_types),
    )


@router.get("/search", response_model=MemberSearchResponse)
async def search_members(
    name: str = Query(..., min_length=2, description="Name or constituency to search for"),
    db: AsyncSession = Depends(get_db),
):
    """Search Parliament Members API by name and constituency."""
    async with httpx.AsyncClient(timeout=30) as http:
        responses = await asyncio.gather(
            http.get(
                f"{MEMBERS_API}/Members/Search",
                params={"Name": name, "skip": 0, "take": 10},
            ),
            http.get(
                f"{MEMBERS_API}/Members/Search",
                params={"Location": name, "skip": 0, "take": 10},
            ),
        )

    for response in responses:
        response.raise_for_status()

    items_by_member_id: dict[int, dict] = {}
    match_types_by_member_id: dict[int, set[str]] = {}
    search_types = ("name", "location")
    for search_type, response in zip(search_types, responses, strict=True):
        for item in response.json().get("items", []):
            mid = _extract_member_search_id(item)
            if mid is None:
                continue
            items_by_member_id.setdefault(mid, item)
            match_types_by_member_id.setdefault(mid, set()).add(search_type)

    items = list(items_by_member_id.values())
    seen_member_ids = set(items_by_member_id)

    total = len(items)

    # Check which members are already tracked
    parliament_ids = list(seen_member_ids)

    tracked_ids: set[int] = set()
    if parliament_ids:
        result = await db.execute(
            select(Person.parliament_id).where(
                Person.parliament_id.in_(parliament_ids),
                Person.is_tracked.is_(True),
            )
        )
        tracked_ids = {row[0] for row in result}

    results = []
    for item in items:
        mid = _extract_member_search_id(item)
        if mid is None:
            continue
        result = _build_member_search_result(
            item,
            tracked_ids,
            match_types_by_member_id.get(mid, set()),
        )
        if result is not None:
            results.append(result)

    return MemberSearchResponse(results=results, total=total)


@router.get("", response_model=TrackedMemberListResponse)
async def list_tracked_members(
    db: AsyncSession = Depends(get_db),
):
    """List all tracked MPs with vote/question counts."""
    vote_count_subq = (
        select(func.count(DivisionVote.id))
        .where(DivisionVote.person_id == Person.id)
        .correlate(Person)
        .scalar_subquery()
    )
    question_count_subq = (
        select(func.count(WrittenQuestion.id))
        .where(WrittenQuestion.asking_member_id == Person.parliament_id)
        .correlate(Person)
        .scalar_subquery()
    )

    stmt = (
        select(
            Person,
            vote_count_subq.label("vote_count"),
            question_count_subq.label("question_count"),
        )
        .where(Person.is_tracked.is_(True))
        .order_by(Person.name_display)
    )
    result = await db.execute(stmt)

    members = []
    for person, vote_count, question_count in result:
        members.append(
            TrackedMemberSummary(
                parliament_id=person.parliament_id,
                name_display=person.name_display,
                party=person.party,
                house=person.house,
                constituency=person.constituency,
                thumbnail_url=person.thumbnail_url,
                is_active=person.is_active,
                last_refreshed_at=person.last_refreshed_at,
                vote_count=vote_count or 0,
                question_count=question_count or 0,
            )
        )

    return TrackedMemberListResponse(members=members)


@router.post("/{parliament_id}/track")
async def track_member(
    parliament_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Start tracking an MP. Fetches their profile if not already in the database."""
    person = (
        await db.execute(
            select(Person).where(Person.parliament_id == parliament_id)
        )
    ).scalar_one_or_none()

    if not person:
        # Fetch from Parliament API
        async with httpx.AsyncClient(timeout=30) as http:
            try:
                resp = await http.get(f"{MEMBERS_API}/Members/{parliament_id}")
                resp.raise_for_status()
                raw = resp.json()
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=502, detail=f"Failed to fetch member from Parliament API: {exc}"
                ) from exc

        value = raw.get("value", raw)

        party_name = None
        latest_party = value.get("latestParty")
        if isinstance(latest_party, dict):
            party_name = latest_party.get("name")

        house_name = None
        constituency = None
        is_active = True
        house_membership = value.get("latestHouseMembership")
        if isinstance(house_membership, dict):
            house_int = house_membership.get("house")
            house_name = "Commons" if house_int == 1 else ("Lords" if house_int == 2 else None)
            constituency = house_membership.get("membershipFrom")
            membership_status = house_membership.get("membershipStatus")
            if isinstance(membership_status, dict):
                is_active = membership_status.get("statusIsActive", True)

        person = Person(
            parliament_id=parliament_id,
            name_display=value.get("nameDisplayAs", "Unknown"),
            name_list=value.get("nameListAs"),
            party=party_name,
            house=house_name,
            constituency=constituency,
            thumbnail_url=value.get("thumbnailUrl"),
            is_active=is_active,
            is_tracked=True,
        )
        db.add(person)
    else:
        person.is_tracked = True

    await db.commit()
    await db.refresh(person)

    return {
        "status": "tracked",
        "parliament_id": person.parliament_id,
        "name_display": person.name_display,
    }


@router.delete("/{parliament_id}/track")
async def untrack_member(
    parliament_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Stop tracking an MP. Data is preserved."""
    person = (
        await db.execute(
            select(Person).where(Person.parliament_id == parliament_id)
        )
    ).scalar_one_or_none()

    if not person:
        raise HTTPException(status_code=404, detail="Member not found")

    person.is_tracked = False
    await db.commit()

    return {"status": "untracked", "parliament_id": parliament_id}


@router.get("/{parliament_id}", response_model=TrackedMemberSummary)
async def get_member_detail(
    parliament_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get detail for a single member."""
    person = (
        await db.execute(
            select(Person).where(Person.parliament_id == parliament_id)
        )
    ).scalar_one_or_none()

    if not person:
        raise HTTPException(status_code=404, detail="Member not found")

    vote_count = (
        await db.execute(
            select(func.count(DivisionVote.id)).where(DivisionVote.person_id == person.id)
        )
    ).scalar() or 0

    question_count = (
        await db.execute(
            select(func.count(WrittenQuestion.id)).where(
                WrittenQuestion.asking_member_id == parliament_id
            )
        )
    ).scalar() or 0

    return TrackedMemberSummary(
        parliament_id=person.parliament_id,
        name_display=person.name_display,
        party=person.party,
        house=person.house,
        constituency=person.constituency,
        thumbnail_url=person.thumbnail_url,
        is_active=person.is_active,
        last_refreshed_at=person.last_refreshed_at,
        vote_count=vote_count,
        question_count=question_count,
    )


@router.get("/{parliament_id}/votes", response_model=MemberVotesResponse)
async def get_member_votes(
    parliament_id: int,
    limit: int = Query(25, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Paginated voting record for an MP."""
    person = (
        await db.execute(
            select(Person).where(Person.parliament_id == parliament_id)
        )
    ).scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Member not found")

    count_stmt = select(func.count(DivisionVote.id)).where(
        DivisionVote.person_id == person.id
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    votes_stmt = (
        select(DivisionVote, Division)
        .join(Division, Division.id == DivisionVote.division_id)
        .where(DivisionVote.person_id == person.id)
        .order_by(Division.date.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(votes_stmt)

    votes = [
        MemberVoteRecord(
            division_id=dv.division_id,
            parliament_division_id=div.parliament_division_id,
            title=div.title,
            date=div.date,
            vote=dv.vote,
            aye_count=div.aye_count,
            no_count=div.no_count,
        )
        for dv, div in result
    ]

    return MemberVotesResponse(
        parliament_id=parliament_id,
        votes=votes,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/{parliament_id}/questions", response_model=MemberQuestionsResponse)
async def get_member_questions(
    parliament_id: int,
    limit: int = Query(25, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Paginated questions asked by an MP."""
    person = (
        await db.execute(
            select(Person).where(Person.parliament_id == parliament_id)
        )
    ).scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Member not found")

    count_stmt = select(func.count(WrittenQuestion.id)).where(
        WrittenQuestion.asking_member_id == parliament_id
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    questions_stmt = (
        select(WrittenQuestion)
        .where(WrittenQuestion.asking_member_id == parliament_id)
        .order_by(WrittenQuestion.date_tabled.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(questions_stmt)

    questions = [
        MemberQuestionRecord(
            question_id=q.id,
            heading=q.heading,
            uin=q.uin,
            house=q.house,
            date_tabled=q.date_tabled,
            date_answered=q.date_answered,
            answering_body=q.answering_body,
            question_text=q.question_text,
            answer_text=q.answer_text,
            answer_source_url=q.answer_source_url,
            official_url=build_written_question_url(q.date_tabled, q.uin),
        )
        for q in result.scalars()
    ]

    return MemberQuestionsResponse(
        parliament_id=parliament_id,
        questions=questions,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/divisions/{parliament_division_id}")
async def get_division_detail(
    parliament_division_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch full division detail from the Commons Divisions API."""
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            resp = await http.get(
                f"{DIVISIONS_API}/division/{parliament_division_id}.json"
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch division detail: {exc}",
            ) from exc

    # Summarise party vote breakdown from the Aye/No voter lists
    def _party_breakdown(voters: list[dict]) -> list[dict]:
        counts: dict[str, dict] = {}
        for voter in voters:
            party = voter.get("Party", "Unknown")
            abbr = voter.get("PartyAbbreviation", party)
            colour = voter.get("PartyColour", "888888")
            if party not in counts:
                counts[party] = {"party": party, "abbreviation": abbr, "colour": colour, "count": 0}
            counts[party]["count"] += 1
        return sorted(counts.values(), key=lambda x: x["count"], reverse=True)

    # Parse the division title for structured components and bill matching
    title = data.get("Title", "")
    parsed = parse_division_title(title)

    matched_bill = None
    if parsed["bill_name"]:
        bill = (
            await db.execute(
                select(Bill).where(Bill.short_title.ilike(f"%{parsed['bill_name']}%"))
            )
        ).scalar_one_or_none()

        if bill:
            # Try to get longTitle from stored raw JSON
            long_title = None
            raw_item = (
                await db.execute(
                    select(RawParliamentItem).where(
                        RawParliamentItem.source_api == "bills",
                        RawParliamentItem.external_id == str(bill.parliament_bill_id),
                    )
                )
            ).scalar_one_or_none()
            if raw_item and isinstance(raw_item.raw_json, dict):
                long_title = raw_item.raw_json.get("longTitle")

            matched_bill = {
                "short_title": bill.short_title,
                "long_title": long_title,
                "current_stage": bill.current_stage,
                "is_act": bill.is_act,
                "is_defeated": bill.is_defeated,
                "parliament_bill_id": bill.parliament_bill_id,
                "bill_url": f"https://bills.parliament.uk/bills/{bill.parliament_bill_id}",
            }
        else:
            # Fallback: search the Bills API directly
            try:
                async with httpx.AsyncClient(timeout=15) as bills_http:
                    search_resp = await bills_http.get(
                        "https://bills-api.parliament.uk/api/v1/Bills",
                        params={
                            "SearchTerm": parsed["bill_name"],
                            "CurrentHouse": "All",
                            "OriginatingHouse": "All",
                        },
                    )
                    search_resp.raise_for_status()
                    results = search_resp.json().get("items", [])
                    if results:
                        api_bill = results[0]
                        bill_id = api_bill.get("billId")
                        # Fetch full bill detail for longTitle
                        detail_resp = await bills_http.get(
                            f"https://bills-api.parliament.uk/api/v1/Bills/{bill_id}"
                        )
                        detail_resp.raise_for_status()
                        full_bill = detail_resp.json()
                        stage = full_bill.get("currentStage")
                        matched_bill = {
                            "short_title": full_bill.get("shortTitle", ""),
                            "long_title": full_bill.get("longTitle"),
                            "current_stage": stage.get("description") if isinstance(stage, dict) else None,
                            "is_act": full_bill.get("isAct", False),
                            "is_defeated": full_bill.get("isDefeated", False),
                            "parliament_bill_id": bill_id,
                            "bill_url": f"https://bills.parliament.uk/bills/{bill_id}",
                        }
            except Exception:
                logger.debug("Bills API fallback failed for %r", parsed["bill_name"])

    return {
        "division_id": data.get("DivisionId"),
        "title": title,
        "date": data.get("Date"),
        "number": data.get("Number"),
        "aye_count": data.get("AyeCount", 0),
        "no_count": data.get("NoCount", 0),
        "is_deferred": data.get("IsDeferred", False),
        "aye_tellers": data.get("AyeTellers"),
        "no_tellers": data.get("NoTellers"),
        "aye_party_breakdown": _party_breakdown(data.get("Ayes", [])),
        "no_party_breakdown": _party_breakdown(data.get("Noes", [])),
        "bill_name": parsed["bill_name"],
        "division_stage": parsed["stage"],
        "division_detail": parsed["detail"],
        "division_category": parsed["category"],
        "matched_bill": matched_bill,
    }


@router.post("/{parliament_id}/refresh")
async def trigger_member_refresh(
    parliament_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Refresh a tracked member's data (profile + voting records)."""
    person = (
        await db.execute(
            select(Person).where(
                Person.parliament_id == parliament_id,
                Person.is_tracked.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Tracked member not found")

    result = run_member_refresh(parliament_id)
    return {"status": "completed", "parliament_id": parliament_id, "result": result}


@router.post("/refresh-all")
async def trigger_refresh_all_members():
    """Refresh data for all tracked members."""
    return run_all_member_refreshes()
