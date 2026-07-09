"""Trazabilidad de importaciones: versión de parser, formato, validación, saldos,
confianza de extracción (sesión 11, docs/18 §7).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("import_batches", sa.Column("parser_version", sa.String(16), nullable=True))
    op.add_column("import_batches", sa.Column("detected_format", sa.String(64), nullable=True))
    op.add_column("import_batches", sa.Column("validation", JSONB(), nullable=True))
    op.add_column("import_batches", sa.Column("opening_balance", sa.Numeric(18, 4), nullable=True))
    op.add_column("import_batches", sa.Column("closing_balance", sa.Numeric(18, 4), nullable=True))
    op.add_column(
        "import_batches", sa.Column("extraction_confidence", sa.Numeric(4, 3), nullable=True)
    )


def downgrade() -> None:
    for column in (
        "extraction_confidence",
        "closing_balance",
        "opening_balance",
        "validation",
        "detected_format",
        "parser_version",
    ):
        op.drop_column("import_batches", column)
