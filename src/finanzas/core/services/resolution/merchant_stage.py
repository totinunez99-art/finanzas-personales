"""MerchantStage: el Merchant Resolver (B2) adaptado al contrato del pipeline.

El motor puro (matching, extractor, confianzas) sigue en merchant_resolver.py
sin cambios; esta capa solo traduce Resolution → ResolutionResult. Deuda B2
pagada: iterar/aplicar/emitir ya no viven aquí sino en el pipeline.
"""

from typing import Any

from finanzas.core.models import Transaction
from finanzas.core.models.enums import EventType
from finanzas.core.services import merchant_resolver
from finanzas.core.services.resolution.base import (
    EventSpec,
    ResolutionContext,
    ResolutionResult,
)


class MerchantStage:
    name = "merchant"

    def prepare(self, ctx: ResolutionContext) -> None:
        if "merchant_rules" in ctx.cache:
            return
        merchant_resolver.ensure_seed_rules(ctx.session, ctx.user)
        ctx.cache["merchant_rules"] = merchant_resolver._active_rules(ctx.session, ctx.user)
        ctx.cache["merchant_rules_by_id"] = {r.id: r for r in ctx.cache["merchant_rules"]}
        ctx.cache["known_merchants"] = merchant_resolver._known_merchants(ctx.session, ctx.user)

    def resolve(self, tx: Transaction, ctx: ResolutionContext) -> ResolutionResult:
        if tx.merchant_source == "user":
            return ResolutionResult(
                resolver=self.name, skipped_reason="protegido: corrección del usuario"
            )
        resolution = merchant_resolver.resolve(
            ctx.session, ctx.user, tx, ctx.cache["merchant_rules"], ctx.cache["known_merchants"]
        )
        if resolution is None:
            return ResolutionResult(
                resolver=self.name,
                skipped_reason="sin evidencia suficiente" if tx.merchant is None else None,
            )
        changes: dict[str, Any] = {}
        if (
            tx.merchant != resolution.merchant
            or tx.merchant_source != resolution.source
            or tx.merchant_confidence != resolution.confidence
        ):
            changes = {
                "merchant": resolution.merchant,
                "merchant_source": resolution.source,
                "merchant_confidence": resolution.confidence,
                "merchant_rule_id": resolution.rule_id,
            }
        return ResolutionResult(
            resolver=self.name,
            changes=changes,
            confidence=resolution.confidence,
            explanation=resolution.explanation,
            evidence={
                "rule_id": resolution.rule_id or "",
                "source": resolution.source,
                "description_norm": tx.description_norm[:80],
            },
            events=(
                (
                    EventSpec(
                        EventType.MERCHANT_RESOLVED,
                        entity="transaction",
                        payload=resolution.to_payload(),
                    ),
                )
                if changes
                else ()
            ),
        )

    def on_applied(self, tx: Transaction, ctx: ResolutionContext, result: ResolutionResult) -> None:
        rule_id = result.changes.get("merchant_rule_id")
        rule = ctx.cache["merchant_rules_by_id"].get(rule_id) if rule_id else None
        if rule is not None:
            rule.hits_count += 1
