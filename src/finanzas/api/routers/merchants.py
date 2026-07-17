"""Merchant Resolver vía HTTP (Sprint 3 B2, docs/21)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from finanzas.api.deps import get_current_user, get_db
from finanzas.core.models import MerchantRule, User
from finanzas.core.services import merchant_resolver

router = APIRouter(prefix="/merchants", tags=["merchants"])


class TeachRequest(BaseModel):
    pattern: str = Field(min_length=3, description="description_norm exacta a enseñar")
    merchant: str = Field(min_length=2, max_length=120)


@router.get("/unresolved")
def unresolved(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict[str, Any]]:
    return merchant_resolver.unresolved_groups(db, user)


@router.post("/teach", status_code=201)
def teach(
    payload: TeachRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return merchant_resolver.teach(db, user, payload.pattern, payload.merchant)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/backfill")
def backfill(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict[str, int]:
    return merchant_resolver.backfill(db, user)


@router.get("/rules")
def rules(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(MerchantRule)
        .where(MerchantRule.user_id == user.id, MerchantRule.is_active)
        .order_by(MerchantRule.origin.desc(), MerchantRule.hits_count.desc())
    ).scalars()
    return [
        {
            "pattern": r.pattern,
            "merchant": r.merchant,
            "matcher": r.matcher_type,
            "origin": r.origin,
            "hits": r.hits_count,
        }
        for r in rows
    ]
