"""Catálogo de flags: contrato tipado (docs/11 §2)."""

import pytest

from finanzas.shared.errors import InvalidFlagValueError, UnknownFlagError
from finanzas.shared.flags import all_flags, get_flag_def, validate_value


def test_defaults_cumplen_su_propio_tipo() -> None:
    for definition in all_flags():
        validate_value(definition.key, definition.default)


def test_flag_desconocido_falla() -> None:
    with pytest.raises(UnknownFlagError):
        get_flag_def("no.existe")


def test_tipo_invalido_falla() -> None:
    with pytest.raises(InvalidFlagValueError):
        validate_value("ai.enabled", "true")  # string donde va bool


def test_bool_no_es_float_valido() -> None:
    # bool es subclase de int en Python; el catálogo NO debe aceptarlo como número.
    with pytest.raises(InvalidFlagValueError):
        validate_value("ai.confidence_threshold", True)


def test_int_es_float_valido() -> None:
    validate_value("ai.monthly_budget_usd", 10)


def test_shadow_mode_arranca_encendido() -> None:
    # Arranque del MVP en modo sombra: decisión de docs/04 §8, no un accidente.
    assert get_flag_def("ai.shadow_mode").default is True
