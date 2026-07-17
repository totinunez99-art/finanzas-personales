"""Normalización financiera: columna flow en transactions (S3-B4, docs/23).

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("flow", sa.String(12), nullable=True))
    op.create_index("ix_transactions_flow", "transactions", ["flow"])


def downgrade() -> None:
    op.drop_index("ix_transactions_flow", "transactions")
    op.drop_column("transactions", "flow")
