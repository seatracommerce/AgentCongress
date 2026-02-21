from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.bill import Bill
from backend.models.debate import Debate
from backend.schemas.bill import BillSchema, BillDetailSchema

router = APIRouter()


@router.get("", response_model=dict)
async def list_bills(
    chamber: str | None = Query(None, description="Filter by chamber: House or Senate"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of bills."""
    query = select(Bill).order_by(Bill.last_action_date.desc().nullslast(), Bill.created_at.desc())
    if chamber:
        query = query.where(Bill.chamber == chamber)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    bills = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [BillSchema.model_validate(b) for b in bills],
    }


@router.get("/{bill_id}", response_model=BillDetailSchema)
async def get_bill(bill_id: int, db: AsyncSession = Depends(get_db)):
    """Return bill detail with linked debate id."""
    result = await db.execute(select(Bill).where(Bill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    # Fetch most recent debate id for this bill
    debate_result = await db.execute(
        select(Debate.id).where(Debate.bill_id == bill_id).order_by(Debate.created_at.desc()).limit(1)
    )
    debate_id = debate_result.scalar_one_or_none()

    schema = BillDetailSchema.model_validate(bill)
    schema.debate_id = debate_id
    return schema
