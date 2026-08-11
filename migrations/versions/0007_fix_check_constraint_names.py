"""Corrige el doble prefijo en los CHECK de transactions (deuda latente desde 0001).

La 0001 declaró las restricciones con el prefijo ya escrito
(`ck_transactions_status_valid`) y la convención de nombres de la metadata volvió
a anteponerlo, dejando en la base `ck_transactions_ck_transactions_status_valid`.
Los modelos generan el nombre simple. El defecto estuvo latente hasta que Alembic
empezó a comparar CHECK constraints en el test anti-deriva (CI #4).

Se corrige HACIA ADELANTE (rename), no reescribiendo la 0001: las bases ya
creadas —incluida la de producción— tienen los nombres erróneos y deben quedar
alineadas igual que una instalación nueva.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RENAMES = (
    ("ck_transactions_ck_transactions_status_valid", "ck_transactions_status_valid"),
    ("ck_transactions_ck_transactions_source_valid", "ck_transactions_source_valid"),
)


def _rename(origen: str, destino: str) -> None:
    """Renombra solo si existe el origen: idempotente y seguro en cualquier base."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = '{origen}'
            ) THEN
                ALTER TABLE transactions RENAME CONSTRAINT "{origen}" TO "{destino}";
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for origen, destino in _RENAMES:
        _rename(origen, destino)


def downgrade() -> None:
    for origen, destino in _RENAMES:
        _rename(destino, origen)
