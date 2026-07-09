"""Cuentas: mínimo para operar el wizard (crear y listar)."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from finanzas.api.deps import get_current_user, get_db
from finanzas.core.models import Account, User
from finanzas.core.models.enums import AccountType

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    bank: str = Field(min_length=1, max_length=64)
    type: AccountType
    currency: str = Field(pattern="^(CLP|UF|USD)$")
    last4: str | None = Field(default=None, pattern=r"^\d{4}$")


def _to_dict(account: Account) -> dict[str, Any]:
    return {
        "id": str(account.id),
        "name": account.name,
        "bank": account.bank,
        "type": account.type,
        "currency": account.currency,
        "last4": account.last4,
        "is_active": account.is_active,
    }


@router.get("")
def list_accounts(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict[str, Any]]:
    accounts = db.execute(
        select(Account).where(Account.user_id == user.id, Account.is_active).order_by(Account.name)
    ).scalars()
    return [_to_dict(a) for a in accounts]


@router.post("", status_code=201)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    account = Account(
        user_id=user.id,
        name=payload.name,
        bank=payload.bank,
        type=payload.type.value,
        currency=payload.currency,
        last4=payload.last4,
    )
    db.add(account)
    db.flush()
    return _to_dict(account)
