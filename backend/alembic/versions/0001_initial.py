"""Initial schema: bills, debates, statements, votes

Revision ID: 0001
Revises:
Create Date: 2026-02-21

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("congress_bill_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("chamber", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=128), nullable=True),
        sa.Column("sponsor", sa.String(length=256), nullable=True),
        sa.Column("bill_type", sa.String(length=16), nullable=True),
        sa.Column("congress_number", sa.Integer(), nullable=True),
        sa.Column("introduced_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_action_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_action_text", sa.Text(), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("debate_triggered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("congress_bill_id"),
    )
    op.create_index(op.f("ix_bills_congress_bill_id"), "bills", ["congress_bill_id"], unique=True)

    op.create_table(
        "debates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("yea_seats", sa.Integer(), nullable=True),
        sa.Column("nay_seats", sa.Integer(), nullable=True),
        sa.Column("present_seats", sa.Integer(), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_to_x_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_debates_bill_id"), "debates", ["bill_id"], unique=False)

    op.create_table(
        "statements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("debate_id", sa.Integer(), nullable=False),
        sa.Column("caucus_id", sa.String(length=64), nullable=False),
        sa.Column("turn_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["debate_id"], ["debates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_statements_debate_id"), "statements", ["debate_id"], unique=False)

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("debate_id", sa.Integer(), nullable=False),
        sa.Column("caucus_id", sa.String(length=64), nullable=False),
        sa.Column("choice", sa.String(length=16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("weighted_seats", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["debate_id"], ["debates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_votes_debate_id"), "votes", ["debate_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_votes_debate_id"), table_name="votes")
    op.drop_table("votes")
    op.drop_index(op.f("ix_statements_debate_id"), table_name="statements")
    op.drop_table("statements")
    op.drop_index(op.f("ix_debates_bill_id"), table_name="debates")
    op.drop_table("debates")
    op.drop_index(op.f("ix_bills_congress_bill_id"), table_name="bills")
    op.drop_table("bills")
