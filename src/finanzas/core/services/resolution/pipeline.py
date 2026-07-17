"""Resolution Pipeline: una sola tubería para todo enriquecimiento (docs/22).

Ejecuta uno, varios o todos los resolvers en orden CONFIGURABLE (flag
resolution.order, docs/11) sin tocar el código de ninguno. El pipeline —no los
resolvers— aplica cambios, emite eventos, cronometra y reporta.
"""

import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from finanzas.core.models import Transaction, User
from finanzas.core.services.events import emit
from finanzas.core.services.resolution.base import ResolutionContext, Resolver
from finanzas.core.services.resolution.category_resolver import CategoryStage
from finanzas.core.services.resolution.flow_stage import FlowStage
from finanzas.core.services.resolution.merchant_stage import MerchantStage
from finanzas.core.services.resolution.stubs import (
    AiResolver,
    AnomalyResolver,
    RecurringResolver,
    SubscriptionResolver,
)
from finanzas.shared.errors import ConfigError
from finanzas.shared.logging import get_logger

logger = get_logger("resolution_pipeline")

REGISTRY: dict[str, type] = {
    "merchant": MerchantStage,
    "category": CategoryStage,
    "flow": FlowStage,
    "recurring": RecurringResolver,
    "subscription": SubscriptionResolver,
    "anomaly": AnomalyResolver,
    "ai": AiResolver,
}
DEFAULT_ORDER = "merchant,category,flow"


def _build_stages(names: list[str] | None, session: Session) -> list[Resolver]:
    if names is None:
        from finanzas.core.services.settings_service import SettingsService

        configured = SettingsService().get(session, "resolution.order")
        names = [n.strip() for n in str(configured).split(",") if n.strip()]
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        raise ConfigError(f"Resolvers desconocidos en el orden: {unknown}")
    return [REGISTRY[n]() for n in names]


def run(
    session: Session,
    user: User,
    resolvers: list[str] | None = None,
    account_id: uuid.UUID | None = None,
    dry_run: bool = False,
    sample_limit: int = 20,
) -> dict[str, Any]:
    """Corre el pipeline. dry_run: calcula y reporta sin escribir NADA."""
    stages = _build_stages(resolvers, session)
    ctx = ResolutionContext(session=session, user=user, dry_run=dry_run)
    # dry-run (revisión sesión 17): se aplica TODO dentro de un SAVEPOINT que se
    # revierte al final → el encadenamiento entre etapas es idéntico al real y la
    # base de datos garantiza cero escritura. Sin esto, category no vería el
    # merchant propuesto y el dry-run subestimaría.
    nested = session.begin_nested() if dry_run else None
    for stage in stages:
        stage.prepare(ctx)

    conditions = [Transaction.user_id == user.id]
    if account_id is not None:
        conditions.append(Transaction.account_id == account_id)
    txs = session.execute(select(Transaction).where(*conditions)).scalars().all()

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "order": [s.name for s in stages],
        "transactions": len(txs),
        "stages": {
            s.name: {"applied": 0, "skipped": 0, "no_change": 0, "total_ms": 0.0} for s in stages
        },
        "samples": [],
    }
    for tx in txs:
        for stage in stages:
            started = time.perf_counter()
            result = stage.resolve(tx, ctx)
            duration_ms = (time.perf_counter() - started) * 1000
            stats = report["stages"][stage.name]
            stats["total_ms"] += duration_ms

            if not result.applied_anything:
                stats["skipped" if result.skipped_reason else "no_change"] += 1
                continue

            if dry_run and len(report["samples"]) < sample_limit:
                payload = result.to_payload()
                payload["duration_ms"] = round(duration_ms, 2)
                payload["transaction"] = tx.description_raw[:60]
                report["samples"].append(payload)

            for field_name, value in result.changes.items():
                if not field_name.startswith("_"):  # metadatos internos del resolver
                    setattr(tx, field_name, value)
            stage.on_applied(tx, ctx, result)
            for event in result.events:
                emit(
                    ctx.session,
                    event.event_type,
                    entity=event.entity,
                    entity_id=tx.id,
                    payload={**event.payload, "duration_ms": round(duration_ms, 2)},
                )
            stats["applied"] += 1

    if nested is not None:
        nested.rollback()  # dry-run: nada persiste, ni cambios ni eventos ni semillas

    for stats in report["stages"].values():
        stats["total_ms"] = round(stats["total_ms"], 1)
    logger.info(
        "pipeline_run",
        dry_run=dry_run,
        **{k: v for k, v in report.items() if k in ("order", "transactions")},
    )
    return report
