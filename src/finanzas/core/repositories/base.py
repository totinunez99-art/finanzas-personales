"""Repositorio base con filtrado obligatorio por usuario (ADR-002).

Toda query sobre datos de usuario pasa por aquí: el filtro user_id no depende
de la disciplina de cada llamada. Los repositorios concretos llegan con las
funcionalidades que los necesiten.
"""

import uuid
from typing import Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from finanzas.core.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class UserScopedRepository(Generic[ModelT]):  # noqa: UP046  # sintaxis clasica deliberada: permite verificar mypy tambien en entornos 3.10
    model: type[ModelT]

    def __init__(self, session: Session, user_id: uuid.UUID) -> None:
        self.session = session
        self.user_id = user_id

    def _base_query(self) -> Select[tuple[ModelT]]:
        return select(self.model).where(self.model.user_id == self.user_id)  # type: ignore[attr-defined]

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        query = self._base_query().where(self.model.id == entity_id)  # type: ignore[attr-defined]
        return self.session.execute(query).scalar_one_or_none()

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity
