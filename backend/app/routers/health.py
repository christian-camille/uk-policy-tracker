from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    health = {"status": "ok", "db": "unknown", "redis": "unknown", "freshness": {}}

    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        health["db"] = "connected"
    except Exception:
        health["db"] = "disconnected"
        health["status"] = "degraded"

    # Check Redis
    try:
        from redis import Redis

        from app.config import get_settings

        settings = get_settings()
        r = Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        r.ping()
        health["redis"] = "connected"
        r.close()
    except Exception:
        health["redis"] = "disconnected"
        health["status"] = "degraded"

    # Source freshness
    try:
        govuk_result = await db.execute(
            text("SELECT MAX(fetched_at) FROM bronze.raw_govuk_items")
        )
        parl_result = await db.execute(
            text("SELECT MAX(fetched_at) FROM bronze.raw_parliament_items")
        )
        govuk_latest = govuk_result.scalar()
        parl_latest = parl_result.scalar()
        health["freshness"] = {
            "govuk_last_fetch": govuk_latest.isoformat() if govuk_latest else None,
            "parliament_last_fetch": parl_latest.isoformat() if parl_latest else None,
        }
    except Exception:
        pass

    return health
