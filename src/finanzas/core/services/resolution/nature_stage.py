"""NatureStage: naturaleza financiera del movimiento (Sprint 4 F1, docs/25 · ADR-011).

Sustituye al FlowStage binario. Responde una pregunta que el modelo anterior no
podía formular: ¿este movimiento CAMBIA el patrimonio o solo lo cambia de FORMA?

    expense | income | finance_cost   → cambian el patrimonio: cuentan en KPIs
    debt | lending | asset | internal → solo cambian su forma: fuera de KPIs

Derivación determinista: la naturaleza ES el `kind` de la categoría asignada.
Sin categoría no se inventa naturaleza (NULL) y NULL cuenta como operacional:
lo no clasificado se MUESTRA, nunca se oculta.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

from sqlalchemy import or_

from finanzas.core.models import Transaction
from finanzas.core.models.enums import EventType
from finanzas.core.services.resolution.base import (
    EventSpec,
    ResolutionContext,
    ResolutionResult,
)

# Catálogo cerrado de naturalezas (docs/25 §3.B).
NATURES = ("expense", "income", "finance_cost", "debt", "lending", "asset", "internal")

# Las únicas que alteran el patrimonio neto → las únicas que cuentan en estadísticas.
OPERATIONAL_NATURES = ("expense", "income", "finance_cost")

_EXPLICACION = {
    "expense": "consumo real: reduce tu patrimonio",
    "income": "ingreso genuino: aumenta tu patrimonio",
    "finance_cost": "costo del dinero (interés, impuesto, comisión): es gasto real",
    "debt": "deuda con una institución: cambia tu efectivo y tu deuda a la vez",
    "lending": "préstamo con una persona: nace o se extingue una cuenta por cobrar",
    "asset": "compra o venta de un bien: el patrimonio cambia de forma, no de tamaño",
    "internal": "movimiento entre cuentas propias: el dinero no salió de tu bolsillo",
}


def operational_condition() -> "ColumnElement[bool]":
    """Condición SQL canónica: qué movimientos cuentan en TODA estadística.

    Única fuente de verdad (ADR-010, ampliada por ADR-011): reporting, insights y
    analytics la importan. NULL = sin clasificar = visible, para no maquillar.
    """
    return or_(
        Transaction.nature.is_(None),
        Transaction.nature.in_(OPERATIONAL_NATURES),
    )


class NatureStage:
    name = "nature"

    def prepare(self, ctx: ResolutionContext) -> None:
        # Reusa el cache del CategoryStage si corrió antes; si no, lo carga
        # (sin dependencia implícita de orden).
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
        if category is None:
            return ResolutionResult(
                resolver=self.name,
                skipped_reason="sin categoría: naturaleza indeterminada (cuenta como operacional)",
            )
        nature = category.kind
        if nature not in NATURES:  # categoría con kind fuera del catálogo: no adivinar
            return ResolutionResult(
                resolver=self.name, skipped_reason=f"kind desconocido en catálogo: {nature!r}"
            )
        if tx.nature == nature:
            return ResolutionResult(resolver=self.name, skipped_reason="sin cambio")

        detalle = f"categoría {category.name!r} es kind={nature}: {_EXPLICACION[nature]}"
        return ResolutionResult(
            resolver=self.name,
            changes={"nature": nature},
            confidence=Decimal("1.00"),  # determinista por definición
            explanation=[
                {"factor": "kind_categoria", "detalle": detalle},
                {
                    "factor": "efecto_patrimonial",
                    "detalle": (
                        "cuenta en KPIs" if nature in OPERATIONAL_NATURES else "excluido de KPIs"
                    ),
                },
            ],
            evidence={
                "category": category.name,
                "nature_previa": tx.nature or "",
                "cuenta_en_kpis": str(nature in OPERATIONAL_NATURES),
            },
            events=(
                EventSpec(
                    EventType.NATURE_ASSIGNED,
                    entity="transaction",
                    payload={"nature": nature, "categoria": category.name},
                ),
            ),
        )

    def on_applied(self, tx: Transaction, ctx: ResolutionContext, result: ResolutionResult) -> None:
        return None
