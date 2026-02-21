from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BillSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    congress_bill_id: str
    title: str
    chamber: str | None
    status: str | None
    sponsor: str | None
    bill_type: str | None
    congress_number: int | None
    introduced_date: datetime | None
    last_action_date: datetime | None
    last_action_text: str | None
    congress_url: str | None
    importance_score: float
    debate_triggered: bool
    created_at: datetime


class BillDetailSchema(BillSchema):
    summary: str | None
    debate_id: int | None = None
