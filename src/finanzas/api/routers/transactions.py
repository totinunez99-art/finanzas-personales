"""Listado de movimientos con búsqueda y filtros (Sprint 2). Router delgado:
la lógica vive en core/services/reporting.py."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from finanzas.api.deps import get_current_user, get_db
from finanzas.core.models import Category, User
from finanzas.core.services.reporting import TransactionFilters, list_transactions

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
def list_endpoint(
    account_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    amount_min: Decimal | None = Query(default=None, ge=0),
    amount_max: Decimal | None = Query(default=None, ge=0),
    kind: str | None = Query(default=None, pattern="^(cargo|abono)$"),
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    total, rows = list_transactions(
        db,
        user,
        TransactionFilters(
            account_id=account_id,
            q=q,
            date_from=date_from,
            date_to=date_to,
            amount_min=amount_min,
            amount_max=amount_max,
            kind=kind,
            limit=limit,
            offset=offset,
        ),
    )
    category_names = {
        c.id: c.name
        for c in db.execute(select(Category).where(Category.user_id == user.id)).scalars()
    }
    items = [
        {
            "id": str(t.id),
            "posted_at": t.posted_at.isoformat(),
            "description": t.description_raw,
            "amount": str(t.amount),
            "currency": t.currency,
            "kind": "cargo" if t.amount < 0 else "abono",
            "category": category_names.get(t.category_id) if t.category_id else None,
            "status": t.status,
            "source": t.source,
        }
        for t in rows
    ]
    return {"total": total, "items": items}
