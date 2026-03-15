from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.entities import EntityDetailResponse
from app.services.graph import GraphService

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("/by-source/{entity_type}/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_by_source(
    entity_type: str,
    entity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return entity details resolved from a source entity type/id pair."""
    service = GraphService(db)
    detail = await service.get_entity_detail_by_source(entity_type, entity_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Entity not found")
    return detail


@router.get("/{node_id}", response_model=EntityDetailResponse)
async def get_entity(
    node_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return node metadata and all connected nodes (1-hop traversal)."""
    service = GraphService(db)
    detail = await service.get_entity_detail(node_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Entity not found")
    return detail
