"""FlowStage: normalización financiera (Sprint 3 B4, docs/23).

Marca cada transacción como flujo 'operational' (cuenta en KPIs/estadísticas)
o 'internal' (movimiento interno: pago de tarjeta, traspasos entre cuentas
propias, reversos). TODA consulta financiera filtra por esta columna:
una sola fuente de verdad, cero lógica duplicada en reporting.

Derivación determinista: categoría con kind='transfer' → internal.
Sin categoría o kind expense/income → operational (lo no clasificado sigue
contando como gasto: ocultarlo sería mentir).
"""

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

from finanzas.core.models import Transaction
from finanzas.core.models.enums import EventType
from finanzas.core.services.resolution.base import (
    EventSpec,
    ResolutionContext,
    ResolutionResult,
)

FLOW_OPERATIONAL = "operational"
FLOW_INTERNAL = "internal"


def operational_condition() -> "ColumnElement[bool]":
    """Condición SQL canónica: excluir movimientos internos de TODA estadística.
    Única fuente (docs/23); flow NULL cuenta como operacional (no ocultar)."""
    return Transaction.flow.is_distinct_from(FLOW_INTERNAL)


class FlowStage:
    name = "flow"

    def prepare(self, ctx: ResolutionContext) -> None:
        # Reusa el cache de categorías del CategoryStage si corrió antes;
        # si no, lo carga (sin dependencia implícita de orden).
        if "categories_by_id" not in ctx.cache:
            from sqlalchemy import select

            from finanzas.core.models import Category

            ctx.cache["categories_by_id"] = {
                c.id: c
                for c in ctx.session.execute(
                    select(Category).where(Category.user_id == ctx.user.id)
                ).scalars()
            }

    def resolve(self, tx: Transaction, ctx: ResolutionContext) -> ResolutionResult:
        category = ctx.cache["categories_by_id"].get(tx.category_id) if tx.category_id else None
        flow = FLOW_INTERNAL if (category and category.kind == "transfer") else FLOW_OPERATIONAL
        if tx.flow == flow:
            return ResolutionResult(resolver=self.name, skipped_reason="sin cambio")
        reason = (
            f"categoría {category.name!r} es kind=transfer (movimiento interno)"
            if flow == FLOW_INTERNAL and category is not None
            else "sin categoría transfer: cuenta en estadísticas operativas"
        )
        return ResolutionResult(
            resolver=self.name,
            changes={"flow": flow},
            confidence=Decimal("1.00"),  # determinista por definición
            explanation=[{"factor": "kind_categoria", "detalle": reason}],
            evidence={"category": category.name if category else "", "kind_previo": tx.flow or ""},
            events=(
                EventSpec(
                    EventType.FLOW_NORMALIZED,
                    entity="transaction",
                    payload={"flow": flow, "reason": reason},
                ),
            ),
        )

    def on_applied(self, tx: Transaction, ctx: ResolutionContext, result: ResolutionResult) -> None:
        return None
