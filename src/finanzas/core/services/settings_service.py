"""Flags dinámicos (docs/11 §2): lectura con caché TTL y escritura auditada.

Precedencia: app_settings (DB) > default del catálogo. El valor se guarda
envuelto como {"v": <valor>} para que JSONB acepte escalares sin ambigüedad.
"""

import time
from typing import Any

from sqlalchemy.orm import Session

from finanzas.core.models import AppSetting
from finanzas.core.models.enums import EventType
from finanzas.core.services.events import emit
from finanzas.shared.config import get_settings
from finanzas.shared.flags import get_flag_def, validate_value


class SettingsService:
    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl = ttl_seconds if ttl_seconds is not None else (
            get_settings().settings_cache_ttl_seconds
        )
        self._cache: dict[str, tuple[float, Any]] = {}

    def get(self, session: Session, key: str) -> Any:
        definition = get_flag_def(key)  # falla temprano si el flag no está declarado
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached is not None and now - cached[0] < self._ttl:
            return cached[1]

        row = session.get(AppSetting, key)
        value = row.value.get("v") if row is not None else definition.default
        self._cache[key] = (now, value)
        return value

    def set(self, session: Session, key: str, value: Any, actor: str = "user") -> None:
        validate_value(key, value)
        row = session.get(AppSetting, key)
        previous = row.value.get("v") if row is not None else get_flag_def(key).default
        if row is None:
            session.add(AppSetting(key=key, value={"v": value}, updated_by=actor))
        else:
            row.value = {"v": value}
            row.updated_by = actor
        emit(
            session,
            EventType.SETTINGS_CHANGED,
            entity="app_setting",
            actor=actor,
            payload={"key": key, "previous": previous, "new": value},
        )
        self._cache.pop(key, None)

    def non_default(self, session: Session) -> dict[str, Any]:
        """Flags con valor distinto al default (visibilidad en página de salud)."""
        from finanzas.shared.flags import all_flags

        result: dict[str, Any] = {}
        for definition in all_flags():
            value = self.get(session, definition.key)
            if value != definition.default:
                result[definition.key] = value
        return result
