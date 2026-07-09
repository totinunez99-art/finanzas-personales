"""Bootstrap idempotente de datos base. Usado por scripts/seed.py y scripts/demo.py
(una sola implementación: docs/08 §2, no duplicar lógica)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from finanzas.core.models import Account, User


def ensure_default_user(session: Session, email: str, display_name: str = "Tomás") -> User:
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, display_name=display_name)
        session.add(user)
        session.flush()
    return user


def ensure_account(
    session: Session,
    user: User,
    name: str,
    bank: str,
    account_type: str,
    currency: str,
) -> tuple[Account, bool]:
    """Devuelve (cuenta, creada_ahora). Idempotente por (user, name)."""
    account = session.execute(
        select(Account).where(Account.user_id == user.id, Account.name == name)
    ).scalar_one_or_none()
    if account is not None:
        return account, False
    account = Account(
        user_id=user.id, name=name, bank=bank, type=account_type, currency=currency
    )
    session.add(account)
    session.flush()
    return account, True
