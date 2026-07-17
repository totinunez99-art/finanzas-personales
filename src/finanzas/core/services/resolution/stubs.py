"""Resolvers futuros: interfaces vacías registradas en el pipeline (docs/22 §5).

Existen para que el orden configurable pueda nombrarlos desde hoy y para que
su implementación futura no toque el pipeline. La IA será uno más, sin
privilegios, al final del orden por defecto cuando llegue.
"""

from finanzas.core.models import Transaction
from finanzas.core.services.resolution.base import (
    ResolutionContext,
    ResolutionResult,
)


class _NotImplementedResolver:
    name = "stub"

    def prepare(self, ctx: ResolutionContext) -> None:
        return None

    def resolve(self, tx: Transaction, ctx: ResolutionContext) -> ResolutionResult:
        return ResolutionResult(resolver=self.name, skipped_reason="no implementado aún")

    def on_applied(self, tx: Transaction, ctx: ResolutionContext, result: ResolutionResult) -> None:
        return None


class RecurringResolver(_NotImplementedResolver):
    name = "recurring"


class SubscriptionResolver(_NotImplementedResolver):
    name = "subscription"


class AnomalyResolver(_NotImplementedResolver):
    name = "anomaly"


class AiResolver(_NotImplementedResolver):
    """Nivel 5: actuará SOLO cuando los deterministas no alcancen confianza.
    Sin privilegios: mismo contrato, mismas reglas de auditoría."""

    name = "ai"
