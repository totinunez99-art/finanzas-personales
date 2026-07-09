"""Cuentas y categorías (docs/03)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from finanzas.core.models.base import Base, TimestampMixin, UuidPkMixin


class Account(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    bank: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16))  # AccountType
    currency: Mapped[str] = mapped_column(String(3))
    last4: Mapped[str | None] = mapped_column(String(4))
    # El saldo se DERIVA: opening_balance + suma de movimientos (docs/03).
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    opening_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Category(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "parent_id", "name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    kind: Mapped[str] = mapped_column(String(10))  # CategoryKind
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Jerarquía máx. 2 niveles: regla de servicio, no de DB (docs/03).
