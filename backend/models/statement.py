from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    debate_id: Mapped[int] = mapped_column(Integer, ForeignKey("debates.id"), nullable=False, index=True)
    caucus_id: Mapped[str] = mapped_column(String(64), nullable=False)
    turn_type: Mapped[str] = mapped_column(String(32), nullable=False)  # opening / debate / closing
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    debate: Mapped["Debate"] = relationship("Debate", back_populates="statements")  # noqa: F821
