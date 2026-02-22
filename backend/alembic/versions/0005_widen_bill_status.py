"""Widen bills.status from VARCHAR(128) to TEXT

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-22

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("bills", "status", type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("bills", "status", type_=sa.String(length=128), existing_nullable=True)
