"""Diagnóstico READ-ONLY del pipeline sobre datos reales (validación Sprint 3, docs/24).

NO modifica el sistema ni persiste nada: reutiliza las etapas REALES dentro de un
SAVEPOINT que se revierte siempre. Su única salida es un informe JSON por stdout.
Script de diagnóstico desechable: no forma parte del runtime.

Uso: type scripts\diagnose_pipeline.py | docker exec -i finanzaspersonales-api-1 python -
"""

import json
from collections import Counter, defaultdict
from decimal import Decimal

from sqlalchemy import select

from finanzas.core.db import session_scope
from finanzas.core.models import Category, Transaction, User
from finanzas.core.services.resolution.base import ResolutionContext
from finanzas.core.services.resolution.category_resolver import CategoryStage
from finanzas.core.services.resolution.merchant_stage import MerchantStage
from finanzas.core.services.resolution.nature_stage import OPERATIONAL_NATURES, NatureStage

FINANCING = ("LINEA DE CREDI", "AMORTIZACION", "PAGO LINEA DE CRED")
CARD = ("PAGO TARJETA DE CREDITO", "PAGO AUTOMATICO TARJETA", "CARGO POR PAGO TC")


def d(x):
    return str(Decimal(x).quantize(Decimal("1")))


with session_scope() as session:
    user = session.execute(select(User)).scalars().first()
    stages = [MerchantStage(), CategoryStage(), NatureStage()]
    ctx = ResolutionContext(session=session, user=user, dry_run=True)
    nested = session.begin_nested()
    for s in stages:
        s.prepare(ctx)

    txs = list(session.execute(select(Transaction).where(Transaction.user_id == user.id)).scalars())
    cats = {
        c.id: c
        for c in session.execute(select(Category).where(Category.user_id == user.id)).scalars()
    }

    stats = {s.name: Counter() for s in stages}
    rules_used = Counter()
    merchant_rules_used = Counter()
    rows = []

    for tx in txs:
        row = {
            "desc": tx.description_raw,
            "amount": str(tx.amount),
            "cat": None,
            "kind": None,
            "flow": None,
            "merchant": None,
        }
        for stage in stages:
            r = stage.resolve(tx, ctx)
            if not r.applied_anything:
                stats[stage.name]["skipped" if r.skipped_reason else "no_change"] += 1
                continue
            stats[stage.name]["applied"] += 1
            if stage.name == "category":
                rules_used[str(r.evidence.get("pattern"))] += 1
            if stage.name == "merchant":
                merchant_rules_used[
                    str(r.evidence.get("pattern") or r.evidence.get("motivo") or "?")
                ] += 1
            for k, v in r.changes.items():
                if not k.startswith("_"):
                    setattr(tx, k, v)
            stage.on_applied(tx, ctx, r)
        row["merchant"] = tx.merchant
        row["nature"] = tx.nature
        if tx.category_id:
            c = cats.get(tx.category_id)
            row["cat"], row["kind"] = (c.name, c.kind) if c else (None, None)
        rows.append(row)

    # --- agregados ---
    by_kind = defaultdict(lambda: {"n": 0, "monto": Decimal(0)})
    by_cat = Counter()
    unclassified = []
    internal_n = 0
    internal_sum = Decimal(0)
    financing = {"n": 0, "abonos": Decimal(0), "cargos": Decimal(0), "clasificados": 0}
    card_ops = {"n": 0, "monto": Decimal(0), "detectados_internos": 0}
    ambiguous = []

    for r in rows:
        amt = Decimal(r["amount"])
        k = r["kind"] or "SIN_CLASIFICAR"
        by_kind[k]["n"] += 1
        by_kind[k]["monto"] += amt
        by_cat[r["cat"] or "SIN_CLASIFICAR"] += 1
        if r["cat"] is None:
            unclassified.append((r["desc"], d(amt)))
        if r["nature"] and r["nature"] not in OPERATIONAL_NATURES:
            internal_n += 1
            internal_sum += abs(amt)
        up = r["desc"].upper()
        if any(f in up for f in FINANCING):
            financing["n"] += 1
            financing["abonos" if amt > 0 else "cargos"] += abs(amt)
            financing["clasificados"] += 1 if r["nature"] == "debt" else 0
        if any(c in up for c in CARD):
            card_ops["n"] += 1
            card_ops["monto"] += abs(amt)
            card_ops["detectados_internos"] += 1 if r["nature"] in ("internal", "debt") else 0
        if up.startswith(("TRASPASO A:", "TRASPASO DE:", "APP-TRASPASO")) and abs(amt) >= 200000:
            ambiguous.append((r["desc"], d(amt), r["cat"]))

    grouped = Counter()
    totals = defaultdict(Decimal)
    for desc, amt in unclassified:
        grouped[desc] += 1
        totals[desc] += abs(Decimal(amt))

    out = {
        "total_movimientos": len(txs),
        "etapas": {n: dict(c) for n, c in stats.items()},
        "distribucion_por_naturaleza": {
            k: {"n": v["n"], "monto_neto": d(v["monto"])} for k, v in sorted(by_kind.items())
        },
        "categorias_asignadas": by_cat.most_common(),
        "naturaleza": {
            "fuera_de_kpis": internal_n,
            "monto_fuera_de_kpis": d(internal_sum),
            "cuentan_en_kpis": len(txs) - internal_n,
        },
        "reglas_categoria_usadas": rules_used.most_common(),
        "reglas_merchant_usadas": merchant_rules_used.most_common(20),
        "sin_clasificar_grupos": [
            {"desc": k, "n": v, "monto": d(totals[k])} for k, v in grouped.most_common(40)
        ],
        "financiamiento_linea_credito": {
            "movimientos": financing["n"],
            "abonos": d(financing["abonos"]),
            "cargos": d(financing["cargos"]),
            "clasificados": financing["clasificados"],
        },
        "operaciones_tarjeta": {
            "movimientos": card_ops["n"],
            "monto": d(card_ops["monto"]),
            "detectados_internos": card_ops["detectados_internos"],
        },
        "ambiguos_transferencias_grandes": ambiguous,
    }
    nested.rollback()
    print("###JSON###")
    print(json.dumps(out, ensure_ascii=False))
