from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Debate(Base):
    __tablename__ = "debates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending / running / completed / failed
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    yea_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nay_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    present_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)  # passed / failed
    chamber: Mapped[str | None] = mapped_column(String(16), nullable=True)  # House / Senate
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_to_x_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    bill: Mapped["Bill"] = relationship("Bill", back_populates="debates")  # noqa: F821
    statements: Mapped[list["Statement"]] = relationship(  # noqa: F821
        "Statement", back_populates="debate", order_by="Statement.sequence"
    )
    votes: Mapped[list["Vote"]] = relationship("Vote", back_populates="debate")


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    debate_id: Mapped[int] = mapped_column(Integer, ForeignKey("debates.id"), nullable=False, index=True)
    caucus_id: Mapped[str] = mapped_column(String(64), nullable=False)
    choice: Mapped[str] = mapped_column(String(16), nullable=False)  # yea / nay / present
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    weighted_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    debate: Mapped["Debate"] = relationship("Debate", back_populates="votes")
