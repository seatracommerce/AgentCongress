from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.debate import Debate
from backend.schemas.debate import DebateSchema, DebateDetailSchema

router = APIRouter()


@router.get("", response_model=dict)
async def list_debates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of debates, newest first."""
    query = select(Debate).order_by(Debate.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    debates = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [DebateSchema.model_validate(d) for d in debates],
    }


@router.get("/{debate_id}", response_model=DebateDetailSchema)
async def get_debate(debate_id: int, db: AsyncSession = Depends(get_db)):
    """Return full debate detail: statements and votes."""
    result = await db.execute(
        select(Debate)
        .where(Debate.id == debate_id)
        .options(
            selectinload(Debate.statements),
            selectinload(Debate.votes),
        )
    )
    debate = result.scalar_one_or_none()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    return DebateDetailSchema.model_validate(debate)
