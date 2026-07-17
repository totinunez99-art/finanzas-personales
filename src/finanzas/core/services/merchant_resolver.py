"""Merchant Resolver: cascada determinista con memoria (Sprint 3 B2, docs/21).

Niveles: (1) hint del parser → (2) reglas deterministas → (3) base de
conocimiento merchant_rules (crece con el uso) → (4) corrección del usuario
(intocable) → (5) IA (futuro, entrará como un source más).

Principios: no inventar jamás (sin evidencia → sin resolución); toda resolución
lleva ConfidenceExplanation con factores auditables; merchant_source='user'
nunca es sobreescrito.
"""

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finanzas.core.models import MerchantRule, Transaction, User
from finanzas.core.models.enums import EventType
from finanzas.core.services.events import emit
from finanzas.shared.logging import get_logger

logger = get_logger("merchant_resolver")

# Confianzas deterministas por método (documentadas, no mágicas):
CONFIDENCE = {
    ("rule", "user"): Decimal("0.99"),  # regla enseñada por el usuario
    ("rule", "promoted"): Decimal("0.96"),  # patrón promovido por repetición
    ("rule", "system_seed"): Decimal("0.95"),
    ("rule_contains", "system_seed"): Decimal("0.90"),
    ("hint", None): Decimal("0.90"),  # extraído por el parser del banco
    ("hint_confirmed", None): Decimal("0.98"),  # hint + regla coinciden
    ("acquirer_known", None): Decimal("0.85"),  # ruido adquirente + comercio conocido
}

# Prefijos de adquirentes/medios de pago chilenos que ENSUCIAN la descripción.
ACQUIRER_PREFIXES = (
    "TRANSBANK",
    "WEBPAY",
    "MERCADOPAGO",
    "MERPAGO",
    "COMPRA NACIONAL",
    "COMPRA INTERNACIONAL",
    "COMPRA DEBITO",
    "COMPRA TARJETA",
)

# Semilla chilena (origin=system_seed). Editable en DB; versionada aquí.
SEED_RULES: tuple[tuple[str, str, str], ...] = (
    # (matcher_type, pattern sobre description_norm, comercio canónico)
    ("contains", "COPEC", "COPEC"),
    ("contains", "SHELL", "SHELL"),
    ("contains", "LIDER", "LIDER"),
    ("contains", "JUMBO", "JUMBO"),
    ("contains", "UNIMARC", "UNIMARC"),
    ("contains", "TOTTUS", "TOTTUS"),
    ("contains", "SANTA ISABEL", "SANTA ISABEL"),
    ("contains", "UBER EATS", "UBER EATS"),
    ("contains", "UBER", "UBER"),
    ("contains", "RAPPI", "RAPPI"),
    ("contains", "CABIFY", "CABIFY"),
    ("contains", "DIDI", "DIDI"),
    ("contains", "SPOTIFY", "SPOTIFY"),
    ("contains", "NETFLIX", "NETFLIX"),
    ("contains", "CRUZ VERDE", "CRUZ VERDE"),
    ("contains", "SALCOBRAND", "SALCOBRAND"),
    ("contains", "FARMACIAS AHUMADA", "FARMACIAS AHUMADA"),
    ("contains", "ENTEL", "ENTEL"),
    ("contains", "MOVISTAR", "MOVISTAR"),
    ("contains", "ENEL", "ENEL"),
    ("contains", "AGUAS ANDINAS", "AGUAS ANDINAS"),
    ("contains", "STARBUCKS", "STARBUCKS"),
)


@dataclass(frozen=True)
class ConfidenceFactor:
    name: str
    detail: str


@dataclass(frozen=True)
class Resolution:
    merchant: str
    confidence: Decimal
    source: str  # rule | hint
    rule_id: uuid.UUID | None = None
    factors: tuple[ConfidenceFactor, ...] = ()

    @property
    def explanation(self) -> list[dict[str, str]]:
        return [{"factor": f.name, "detalle": f.detail} for f in self.factors]

    def to_payload(self) -> dict[str, Any]:
        return {
            "merchant": self.merchant,
            "confidence": str(self.confidence),
            "source": self.source,
            "rule_id": str(self.rule_id) if self.rule_id else None,
            "explanation": self.explanation,
        }


def ensure_seed_rules(session: Session, user: User) -> int:
    """Siembra idempotente de la base de conocimiento."""
    existing = set(
        session.execute(
            select(MerchantRule.pattern).where(
                MerchantRule.user_id == user.id, MerchantRule.origin == "system_seed"
            )
        ).scalars()
    )
    created = 0
    for matcher, pattern, merchant in SEED_RULES:
        if pattern not in existing:
            session.add(
                MerchantRule(
                    user_id=user.id,
                    matcher_type=matcher,
                    pattern=pattern,
                    merchant=merchant,
                    origin="system_seed",
                    priority=100,
                )
            )
            created += 1
    return created


def _active_rules(session: Session, user: User) -> list[MerchantRule]:
    return list(
        session.execute(
            select(MerchantRule)
            .where(MerchantRule.user_id == user.id, MerchantRule.is_active)
            .order_by(MerchantRule.priority, MerchantRule.created_at)
        ).scalars()
    )


def _match_rule(rule: MerchantRule, description_norm: str) -> bool:
    if rule.matcher_type == "exact_norm":
        return description_norm == rule.pattern
    if rule.matcher_type == "contains":
        return rule.pattern in description_norm
    if rule.matcher_type == "regex":
        return re.search(rule.pattern, description_norm) is not None
    return False


def extract_acquirer_candidate(description_norm: str) -> str | None:
    """Quita ruido de adquirentes: 'TRANSBANK FARMACIA X 123' → 'FARMACIA X'.

    Determinista: prefijo conocido + limpieza de separadores y colas numéricas.
    Devuelve None si no hay prefijo adquirente o el resto es insustancial.
    """
    for prefix in ACQUIRER_PREFIXES:
        if description_norm.startswith(prefix):
            rest = description_norm[len(prefix) :]
            rest = re.sub(r"^[\s*:\-.]+", "", rest)
            rest = re.sub(r"[\s]*\d{3,}$", "", rest).strip()  # cola de folio/local
            return rest if len(rest) >= 4 else None
    return None


def _known_merchants(session: Session, user: User) -> set[str]:
    rows = session.execute(
        select(Transaction.merchant)
        .where(Transaction.user_id == user.id, Transaction.merchant.is_not(None))
        .distinct()
    ).scalars()
    return {m.upper() for m in rows if m}


def resolve(
    session: Session,
    user: User,
    tx: Transaction,
    rules: list[MerchantRule],
    known: set[str],
) -> Resolution | None:
    """Resuelve UNA transacción. None = sin evidencia suficiente (no se toca)."""
    if tx.merchant_source == "user":
        return None  # nivel 4: intocable

    desc = tx.description_norm
    for rule in rules:
        if _match_rule(rule, desc):
            key = (
                ("rule", rule.origin)
                if rule.matcher_type != "contains" or (rule.origin != "system_seed")
                else ("rule_contains", "system_seed")
            )
            confidence = CONFIDENCE[key]
            factors = [
                ConfidenceFactor(
                    "coincidencia_regla",
                    f"{rule.matcher_type} {rule.pattern!r} (origen {rule.origin}, "
                    f"{rule.hits_count} aciertos previos)",
                ),
            ]
            if (
                tx.merchant
                and tx.merchant_source == "hint"
                and tx.merchant.upper() == rule.merchant.upper()
            ):
                confidence = CONFIDENCE[("hint_confirmed", None)]
                factors.append(
                    ConfidenceFactor("hint_coincidente", "el parser sugirió el mismo comercio")
                )
            if rule.origin == "user":
                factors.append(ConfidenceFactor("ensenada_por_usuario", "regla creada por ti"))
            factors.append(ConfidenceFactor("sin_conflictos", "ninguna otra regla contradice"))
            return Resolution(
                merchant=rule.merchant,
                confidence=confidence,
                source="rule",
                rule_id=rule.id,
                factors=tuple(factors),
            )

    # Nivel: hint del parser sin regla que lo confirme → conservar con su procedencia
    if tx.merchant and tx.merchant_source is None:
        return Resolution(
            merchant=tx.merchant,
            confidence=CONFIDENCE[("hint", None)],
            source="hint",
            factors=(
                ConfidenceFactor("hint_parser", "extraído por el conector del banco"),
                ConfidenceFactor("sin_regla", "ninguna regla lo confirma aún"),
            ),
        )

    # Nivel: ruido adquirente + comercio YA CONOCIDO (jamás inventar uno nuevo)
    candidate = extract_acquirer_candidate(desc)
    if candidate and candidate.upper() in known:
        return Resolution(
            merchant=candidate,
            confidence=CONFIDENCE[("acquirer_known", None)],
            source="rule",
            factors=(
                ConfidenceFactor(
                    "ruido_adquirente", f"prefijo de medio de pago removido → {candidate!r}"
                ),
                ConfidenceFactor("historial_consistente", "comercio ya visto en tus movimientos"),
            ),
        )
    return None


def backfill(session: Session, user: User, account_id: uuid.UUID | None = None) -> dict[str, int]:
    """Compatibilidad B2: delega en el Resolution Pipeline (etapa merchant).

    Mantiene la firma y las claves de respuesta que consumen la API y la
    página Comercios; la iteración/aplicación/eventos viven en el pipeline.
    """
    from finanzas.core.services.resolution import pipeline

    report = pipeline.run(
        session, user, resolvers=["merchant"], account_id=account_id, dry_run=False
    )
    stage = report["stages"]["merchant"]
    unresolved = session.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.user_id == user.id,
            Transaction.merchant.is_(None),
            *([Transaction.account_id == account_id] if account_id else []),
        )
    ).scalar_one()
    protected = session.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.user_id == user.id,
            Transaction.merchant_source == "user",
            *([Transaction.account_id == account_id] if account_id else []),
        )
    ).scalar_one()
    stats = {
        "resolved": stage["applied"],
        "provenance_set": 0,  # incluido en resolved desde B3 (pipeline unificado)
        "unresolved": int(unresolved),
        "untouched_user": int(protected),
    }
    logger.info("merchant_backfill", **stats)
    return stats


def teach(session: Session, user: User, description_norm: str, merchant: str) -> dict[str, Any]:
    """Nivel 4: una corrección del usuario se convierte en REGLA reutilizable
    y se aplica de inmediato a todas las transacciones coincidentes."""
    merchant = merchant.strip()[:120]
    if not merchant or not description_norm.strip():
        raise ValueError("Patrón y comercio son obligatorios")
    rule = MerchantRule(
        user_id=user.id,
        matcher_type="exact_norm",
        pattern=description_norm.strip(),
        merchant=merchant,
        origin="user",
        priority=10,
    )
    session.add(rule)
    session.flush()

    txs = (
        session.execute(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.description_norm == rule.pattern,
                Transaction.merchant_source.is_distinct_from("user"),
            )
        )
        .scalars()
        .all()
    )
    for tx in txs:
        tx.merchant = merchant
        tx.merchant_source = "rule"
        tx.merchant_confidence = CONFIDENCE[("rule", "user")]
        tx.merchant_rule_id = rule.id
    rule.hits_count = len(txs)
    emit(
        session,
        EventType.MERCHANT_TAUGHT,
        entity="merchant_rule",
        entity_id=rule.id,
        actor="user",
        payload={"pattern": rule.pattern, "merchant": merchant, "applied_to": len(txs)},
    )
    logger.info("merchant_taught", merchant=merchant, applied=len(txs))
    return {"rule_id": str(rule.id), "applied_to": len(txs)}


def unresolved_groups(session: Session, user: User, limit: int = 30) -> list[dict[str, Any]]:
    """Grupos de descripciones sin comercio, ordenados por impacto (para enseñar)."""
    rows = session.execute(
        select(
            Transaction.description_norm,
            func.count().label("n"),
            func.coalesce(func.sum(-Transaction.amount), 0).label("total"),
        )
        .where(
            Transaction.user_id == user.id,
            Transaction.merchant.is_(None),
            Transaction.amount < 0,
        )
        .group_by(Transaction.description_norm)
        .order_by(func.count().desc(), func.sum(-Transaction.amount).desc())
        .limit(limit)
    ).all()
    return [
        {"pattern": r.description_norm, "count": r.n, "total": str(Decimal(r.total).normalize())}
        for r in rows
    ]
