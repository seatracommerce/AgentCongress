from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    congress_bill_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    chamber: Mapped[str | None] = mapped_column(String(16), nullable=True)  # House / Senate
    status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sponsor: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bill_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # hr, s, hjres, etc.
    congress_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    introduced_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_action_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_action_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    congress_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    real_vote_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    real_vote_yea: Mapped[int | None] = mapped_column(Integer, nullable=True)
    real_vote_nay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    real_vote_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    real_vote_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    debate_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    debates: Mapped[list["Debate"]] = relationship("Debate", back_populates="bill")  # noqa: F821
