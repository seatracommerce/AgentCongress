from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StatementSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debate_id: int
    caucus_id: str
    turn_type: str
    content: str
    sequence: int
    created_at: datetime


class VoteSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debate_id: int
    caucus_id: str
    choice: str
    rationale: str | None
    weighted_seats: int
    created_at: datetime


class DebateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bill_id: int
    status: str
    summary: str | None
    yea_seats: int | None
    nay_seats: int | None
    present_seats: int | None
    result: str | None
    chamber: str | None
    started_at: datetime | None
    completed_at: datetime | None
    published_to_x_at: datetime | None
    created_at: datetime


class DebateDetailSchema(DebateSchema):
    statements: list[StatementSchema] = []
    votes: list[VoteSchema] = []
