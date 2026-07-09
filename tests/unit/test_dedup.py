"""Normalización y hash de deduplicación (docs/03 §4)."""

from datetime import date
from decimal import Decimal

from finanzas.core.services.dedup import compute_dedup_hash, normalize_description


def test_normalizacion_canonica() -> None:
    assert normalize_description("  Compra   Líder  ") == "COMPRA LIDER"
    assert normalize_description("café ñuñoa") == "CAFE NUNOA"


def test_hash_estable() -> None:
    args = ("acc-1", date(2026, 7, 1), Decimal("-12500"), "CLP", "COMPRA LIDER")
    assert compute_dedup_hash(*args) == compute_dedup_hash(*args)


def test_hash_ignora_ceros_espurios_del_monto() -> None:
    base = ("acc-1", date(2026, 7, 1))
    h1 = compute_dedup_hash(*base, Decimal("-10.50"), "USD", "X")
    h2 = compute_dedup_hash(*base, Decimal("-10.5000"), "USD", "X")
    assert h1 == h2


def test_hash_cambia_con_cada_campo() -> None:
    base = compute_dedup_hash("acc-1", date(2026, 7, 1), Decimal("-100"), "CLP", "X")
    assert base != compute_dedup_hash("acc-2", date(2026, 7, 1), Decimal("-100"), "CLP", "X")
    assert base != compute_dedup_hash("acc-1", date(2026, 7, 2), Decimal("-100"), "CLP", "X")
    assert base != compute_dedup_hash("acc-1", date(2026, 7, 1), Decimal("-101"), "CLP", "X")
    assert base != compute_dedup_hash("acc-1", date(2026, 7, 1), Decimal("-100"), "USD", "X")
    assert base != compute_dedup_hash("acc-1", date(2026, 7, 1), Decimal("-100"), "CLP", "Y")


def test_intra_day_seq_discrimina_compras_identicas() -> None:
    # Dos cafés idénticos el mismo día: caso borde de docs/03 §4.
    args = ("acc-1", date(2026, 7, 1), Decimal("-4500"), "CLP", "STARBUCKS")
    assert compute_dedup_hash(*args, intra_day_seq=0) != compute_dedup_hash(*args, intra_day_seq=1)
