"""Catálogo de eventos (ADR-009): cerrado y con convención de nombres."""

from finanzas.core.models.enums import EventType


def test_todos_los_eventos_tienen_formato_entidad_punto_accion() -> None:
    for event in EventType:
        assert "." in event.value, f"{event.value} no cumple 'entidad.accion'"
        entity, action = event.value.split(".", 1)
        assert entity and action
        assert event.value == event.value.lower()
