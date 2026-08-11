"""Naturaleza del movimiento: reemplaza flow binario (Sprint 4 F1, docs/25, ADR-011).

flow (operational|internal) no podía representar deuda, préstamos ni venta de bienes:
evidencia en docs/24 §6 sobre 114 movimientos reales. nature es el dominio ampliado.
Seguro: en producción flow estaba 100% NULL (el pipeline nunca se ejecutó).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_transactions_flow", table_name="transactions")
    op.drop_column("transactions", "flow")
    op.add_column("transactions", sa.Column("nature", sa.String(16), nullable=True))
    op.create_index("ix_transactions_nature", "transactions", ["nature"])

    # El kind de la categoría ES la naturaleza: se amplía el dominio Y el ancho
    # (finance_cost no cabía en varchar(10): detectado en pruebas de integración).
    op.alter_column("categories", "kind", type_=sa.String(16), existing_nullable=False)
    op.execute("UPDATE categories SET kind = 'internal' WHERE kind = 'transfer'")
    op.execute(
        "UPDATE categories SET kind = 'finance_cost' "
        "WHERE name IN ('Intereses', 'Comisiones Bancarias')"
    )


def downgrade() -> None:
    op.execute("UPDATE categories SET kind = 'transfer' WHERE kind = 'internal'")
    op.execute("UPDATE categories SET kind = 'income' WHERE name = 'Intereses'")
    op.execute("UPDATE categories SET kind = 'expense' WHERE name = 'Comisiones Bancarias'")
    op.alter_column("categories", "kind", type_=sa.String(10), existing_nullable=False)
    op.drop_index("ix_transactions_nature", table_name="transactions")
    op.drop_column("transactions", "nature")
    op.add_column("transactions", sa.Column("flow", sa.String(12), nullable=True))
    op.create_index("ix_transactions_flow", "transactions", ["flow"])
