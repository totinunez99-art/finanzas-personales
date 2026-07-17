"""Category Resolver: reglas deterministas sobre la infraestructura ADR-008.

Cada asignación crea una ClassificationDecision auditada (decided_by=rule,
rule_id, confianza) y denormaliza el estado en la transacción. Regla dura de
ADR-008: una decisión del usuario JAMÁS es superseded por reglas o IA.
Semillas chilenas de categorías y reglas versionadas aquí (editables en DB).
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from finanzas.core.models import (
    Category,
    ClassificationDecision,
    ClassificationRule,
    Transaction,
    User,
)
from finanzas.core.models.enums import EventType
from finanzas.core.services.resolution.base import (
    EventSpec,
    ResolutionContext,
    ResolutionResult,
)

CONFIDENCE = {
    ("user", "merchant_exact"): Decimal("0.99"),
    ("user", "description_contains"): Decimal("0.97"),
    ("promoted", "merchant_exact"): Decimal("0.96"),
    ("system_seed", "merchant_exact"): Decimal("0.95"),
    ("system_seed", "description_contains"): Decimal("0.90"),
}

# (nombre, kind). Nivel 1 plano para el MVP; jerarquía cuando la realidad la pida.
SEED_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("Supermercado", "expense"),
    ("Combustible", "expense"),
    ("Transporte", "expense"),
    ("Restaurantes y Delivery", "expense"),
    ("Salud y Farmacia", "expense"),
    ("Servicios Básicos", "expense"),
    ("Telecomunicaciones", "expense"),
    ("Arriendo y Vivienda", "expense"),
    ("Seguros", "expense"),
    ("Suscripciones", "expense"),
    ("Compras y Tiendas", "expense"),
    ("Educación", "expense"),
    ("Entretenimiento", "expense"),
    ("Comisiones Bancarias", "expense"),
    ("Transferencias Enviadas", "expense"),
    ("Otros Gastos", "expense"),
    ("Sueldo", "income"),
    ("Transferencias Recibidas", "income"),
    ("Intereses", "income"),
    ("Otros Ingresos", "income"),
    ("Pago de Tarjeta", "transfer"),
    ("Reversos y Ajustes", "transfer"),
    ("Transferencias entre Cuentas", "transfer"),
)

# (matcher, patrón, categoría). merchant_exact evalúa tx.merchant;
# description_contains evalúa description_norm.
SEED_RULES: tuple[tuple[str, str, str], ...] = (
    ("merchant_exact", "COPEC", "Combustible"),
    ("merchant_exact", "SHELL", "Combustible"),
    ("merchant_exact", "LIDER", "Supermercado"),
    ("merchant_exact", "JUMBO", "Supermercado"),
    ("merchant_exact", "UNIMARC", "Supermercado"),
    ("merchant_exact", "TOTTUS", "Supermercado"),
    ("merchant_exact", "SANTA ISABEL", "Supermercado"),
    ("merchant_exact", "UBER EATS", "Restaurantes y Delivery"),
    ("merchant_exact", "RAPPI", "Restaurantes y Delivery"),
    ("merchant_exact", "STARBUCKS", "Restaurantes y Delivery"),
    ("merchant_exact", "UBER", "Transporte"),
    ("merchant_exact", "CABIFY", "Transporte"),
    ("merchant_exact", "DIDI", "Transporte"),
    ("merchant_exact", "CRUZ VERDE", "Salud y Farmacia"),
    ("merchant_exact", "SALCOBRAND", "Salud y Farmacia"),
    ("merchant_exact", "FARMACIAS AHUMADA", "Salud y Farmacia"),
    ("merchant_exact", "ENEL", "Servicios Básicos"),
    ("merchant_exact", "AGUAS ANDINAS", "Servicios Básicos"),
    ("merchant_exact", "ENTEL", "Telecomunicaciones"),
    ("merchant_exact", "MOVISTAR", "Telecomunicaciones"),
    ("merchant_exact", "NETFLIX", "Suscripciones"),
    ("merchant_exact", "SPOTIFY", "Suscripciones"),
    ("description_contains", "ARRIENDO", "Arriendo y Vivienda"),
    ("description_contains", "SUELDO", "Sueldo"),
    ("description_contains", "PRIMA SEGURO", "Seguros"),
    ("description_contains", "SEGURO PROTECCION", "Seguros"),
    ("description_contains", "CARGO POR PAGO TC", "Pago de Tarjeta"),
    ("description_contains", "TRASPASO DE:", "Transferencias Recibidas"),
    ("description_contains", "TRASPASO A:", "Transferencias Enviadas"),
    ("description_contains", "INTERES", "Intereses"),
    ("description_contains", "COMISION", "Comisiones Bancarias"),
    ("description_contains", "REVERSA", "Reversos y Ajustes"),
    ("description_contains", "ANULACION", "Reversos y Ajustes"),
)


def ensure_seed(session: Any, user: User) -> dict[str, int]:
    """Siembra idempotente de categorías y reglas de clasificación."""
    categories = {
        c.name: c
        for c in session.execute(select(Category).where(Category.user_id == user.id)).scalars()
    }
    created_categories = 0
    for name, kind in SEED_CATEGORIES:
        if name not in categories:
            category = Category(user_id=user.id, name=name, kind=kind, is_system=True)
            session.add(category)
            categories[name] = category
            created_categories += 1
    session.flush()

    existing_rules = set(
        session.execute(
            select(ClassificationRule.pattern, ClassificationRule.matcher_type).where(
                ClassificationRule.user_id == user.id,
                ClassificationRule.origin == "system_seed",
            )
        ).all()
    )
    created_rules = 0
    for matcher, pattern, category_name in SEED_RULES:
        if (pattern, matcher) not in existing_rules:
            session.add(
                ClassificationRule(
                    user_id=user.id,
                    matcher_type=matcher,
                    pattern=pattern,
                    category_id=categories[category_name].id,
                    origin="system_seed",
                    priority=100,
                )
            )
            created_rules += 1
    return {"categories": created_categories, "rules": created_rules}


class CategoryStage:
    name = "category"

    def prepare(self, ctx: ResolutionContext) -> None:
        if "category_rules" in ctx.cache:
            return
        ensure_seed(ctx.session, ctx.user)
        ctx.cache["category_rules"] = list(
            ctx.session.execute(
                select(ClassificationRule)
                .where(
                    ClassificationRule.user_id == ctx.user.id,
                    ClassificationRule.is_active,
                )
                .order_by(ClassificationRule.priority, ClassificationRule.created_at)
            ).scalars()
        )
        ctx.cache["categories_by_id"] = {
            c.id: c
            for c in ctx.session.execute(
                select(Category).where(Category.user_id == ctx.user.id)
            ).scalars()
        }
        # decisión vigente por transacción (una consulta, no N)
        ctx.cache["current_decisions"] = {
            d.transaction_id: d
            for d in ctx.session.execute(
                select(ClassificationDecision).where(
                    ClassificationDecision.user_id == ctx.user.id,
                    ClassificationDecision.is_current,
                )
            ).scalars()
        }

    @staticmethod
    def _match(rule: ClassificationRule, tx: Transaction) -> bool:
        if rule.matcher_type == "merchant_exact":
            return tx.merchant is not None and tx.merchant.upper() == rule.pattern.upper()
        if rule.matcher_type == "description_contains":
            return rule.pattern in tx.description_norm
        if rule.matcher_type == "regex":
            import re

            return re.search(rule.pattern, tx.description_norm) is not None
        return False

    def resolve(self, tx: Transaction, ctx: ResolutionContext) -> ResolutionResult:
        current = ctx.cache["current_decisions"].get(tx.id)
        if current is not None and current.decided_by == "user":
            return ResolutionResult(
                resolver=self.name, skipped_reason="protegido: decisión del usuario (ADR-008)"
            )
        for rule in ctx.cache["category_rules"]:
            if not self._match(rule, tx):
                continue
            if current is not None and current.category_id == rule.category_id:
                return ResolutionResult(
                    resolver=self.name, skipped_reason="ya clasificada igual (idempotente)"
                )
            category = ctx.cache["categories_by_id"][rule.category_id]
            confidence = CONFIDENCE.get((rule.origin, rule.matcher_type), Decimal("0.90"))
            explanation = [
                {
                    "factor": "coincidencia_regla",
                    "detalle": f"{rule.matcher_type} {rule.pattern!r} → {category.name} "
                    f"(origen {rule.origin}, {rule.hits_count} aciertos previos)",
                },
                {"factor": "sin_conflictos", "detalle": "primera regla en orden de prioridad"},
            ]
            return ResolutionResult(
                resolver=self.name,
                changes={
                    "category_id": rule.category_id,
                    "classified_by": "rule",
                    "classification_confidence": confidence,
                    "_decision_rule_id": rule.id,  # metadato para on_applied (no columna)
                },
                confidence=confidence,
                explanation=explanation,
                evidence={
                    "rule_id": rule.id,
                    "pattern": rule.pattern,
                    "category": category.name,
                    "superseded_decision": current.id if current else "",
                },
                events=(
                    EventSpec(
                        EventType.TRANSACTION_CLASSIFIED,
                        entity="transaction",
                        payload={
                            "category": category.name,
                            "rule": rule.pattern,
                            "confidence": str(confidence),
                            "explanation": explanation,
                        },
                    ),
                ),
            )
        return ResolutionResult(resolver=self.name, skipped_reason="ninguna regla coincide")

    def on_applied(self, tx: Transaction, ctx: ResolutionContext, result: ResolutionResult) -> None:
        """Auditoría ADR-008: decisión nueva + supersede de la anterior + hits."""
        rule_id = result.changes["_decision_rule_id"]
        decision = ClassificationDecision(
            user_id=ctx.user.id,
            transaction_id=tx.id,
            decided_by="rule",
            rule_id=rule_id,
            category_id=result.changes["category_id"],
            merchant=tx.merchant,
            confidence=result.changes["classification_confidence"],
            is_current=True,
        )
        previous = ctx.cache["current_decisions"].get(tx.id)
        if previous is not None:
            previous.is_current = False
        ctx.session.add(decision)
        ctx.session.flush()
        if previous is not None:
            previous.superseded_by_id = decision.id
        ctx.cache["current_decisions"][tx.id] = decision
        for rule in ctx.cache["category_rules"]:
            if rule.id == rule_id:
                rule.hits_count += 1
                break
