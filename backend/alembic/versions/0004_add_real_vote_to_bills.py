"""Add real vote columns to bills

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-22

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bills", sa.Column("real_vote_result", sa.String(length=32), nullable=True))
    op.add_column("bills", sa.Column("real_vote_yea", sa.Integer(), nullable=True))
    op.add_column("bills", sa.Column("real_vote_nay", sa.Integer(), nullable=True))
    op.add_column("bills", sa.Column("real_vote_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bills", sa.Column("real_vote_description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bills", "real_vote_description")
    op.drop_column("bills", "real_vote_date")
    op.drop_column("bills", "real_vote_nay")
    op.drop_column("bills", "real_vote_yea")
    op.drop_column("bills", "real_vote_result")
