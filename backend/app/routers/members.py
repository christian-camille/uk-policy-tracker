import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.silver import Division, DivisionVote, Person, WrittenQuestion
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
from app.services.parliament import MEMBERS_API

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/members", tags=["members"])


@router.get("/search", response_model=MemberSearchResponse)
async def search_members(
    name: str = Query(..., min_length=2, description="Name to search for"),
    db: AsyncSession = Depends(get_db),
):
    """Search Parliament Members API by name."""
    async with httpx.AsyncClient(timeout=30) as http:
        params = {"Name": name, "skip": 0, "take": 10}
        resp = await http.get(f"{MEMBERS_API}/Members/Search", params=params)
        resp.raise_for_status()
        data = resp.json()

    items = data.get("items", [])
    total = data.get("totalResults", len(items))

    # Check which members are already tracked
    parliament_ids = []
    for item in items:
        value = item.get("value", item)
        mid = value.get("id")
        if mid:
            parliament_ids.append(mid)

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
        value = item.get("value", item)
        mid = value.get("id")
        if not mid:
            continue

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

        results.append(
            MemberSearchResult(
                parliament_id=mid,
                name_display=value.get("nameDisplayAs", "Unknown"),
                party=party_name,
                house=house_name,
                constituency=constituency,
                thumbnail_url=value.get("thumbnailUrl"),
                is_active=is_active,
                is_tracked=mid in tracked_ids,
            )
        )

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
            date_tabled=q.date_tabled,
            date_answered=q.date_answered,
            answering_body=q.answering_body,
            question_text=q.question_text,
        )
        for q in result.scalars()
    ]

    return MemberQuestionsResponse(
        parliament_id=parliament_id,
        questions=questions,
        total=total,
        has_more=(offset + limit) < total,
    )


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
