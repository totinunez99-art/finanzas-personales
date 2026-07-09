"""Usuario. Mono-usuario en MVP; el modelo no lo asume (ADR-002)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from finanzas.core.models.base import Base, CreatedAtMixin, UuidPkMixin


class User(Base, UuidPkMixin, CreatedAtMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    # Sin password: sistema local sin login (docs/06 §1). Auth llega en Fase 7.
