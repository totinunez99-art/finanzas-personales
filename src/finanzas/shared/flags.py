"""Catálogo tipado de feature flags dinámicos (docs/11 §2).

Todo flag debe declararse aquí antes de poder leerse o escribirse.
Los valores en runtime viven en la tabla `app_settings`; este módulo solo
define el contrato (tipo, default, dueño). Strings mágicos prohibidos.
"""

from dataclasses import dataclass
from typing import Any

from finanzas.shared.errors import InvalidFlagValueError, UnknownFlagError


@dataclass(frozen=True)
class FlagDef:
    key: str
    value_type: type
    default: Any
    description: str
    owner: str = "tomas"
    experimental: bool = False


_CATALOG: dict[str, FlagDef] = {
    f.key: f
    for f in [
        FlagDef(
            key="ai.enabled",
            value_type=bool,
            default=True,
            description="OFF: nada llama al LLM; lo no resuelto por reglas va a revisión.",
        ),
        FlagDef(
            key="ai.provider_override",
            value_type=str,
            default="",
            description="Fuerza un proveedor LLM sin tocar .env (vacío = usar .env).",
        ),
        FlagDef(
            key="ai.shadow_mode",
            value_type=bool,
            default=True,
            description="ON: la IA sugiere pero no auto-asigna (arranque del MVP, docs/04 §8).",
        ),
        FlagDef(
            key="ai.auto_classify",
            value_type=bool,
            default=True,
            description="OFF: el pipeline corre pero solo sugiere.",
        ),
        FlagDef(
            key="ai.confidence_threshold",
            value_type=float,
            default=0.85,
            description="Umbral de auto-asignación; se calibra con datos reales.",
        ),
        FlagDef(
            key="ai.monthly_budget_usd",
            value_type=float,
            default=5.0,
            description="Presupuesto mensual LLM; superado, la IA se apaga (docs/11).",
        ),
        FlagDef(
            key="connectors.email_polling",
            value_type=bool,
            default=True,
            description="Apaga el polling IMAP sin apagar el worker.",
        ),
    ]
}


def get_flag_def(key: str) -> FlagDef:
    try:
        return _CATALOG[key]
    except KeyError as exc:
        raise UnknownFlagError(f"Flag no declarado en el catálogo: {key!r}") from exc


def all_flags() -> tuple[FlagDef, ...]:
    return tuple(_CATALOG.values())


def validate_value(key: str, value: object) -> None:
    """Valida tipo contra el catálogo. bool NO es aceptable donde se espera float/int."""
    definition = get_flag_def(key)
    expected = definition.value_type
    if expected is float and isinstance(value, int) and not isinstance(value, bool):
        return  # un int es un float válido
    if not isinstance(value, expected) or (expected is not bool and isinstance(value, bool)):
        raise InvalidFlagValueError(
            f"Flag {key!r}: se esperaba {expected.__name__}, llegó {type(value).__name__}"
        )
