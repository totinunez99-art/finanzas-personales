"""Extractor de ruido adquirente (determinista, sin invención)."""

from finanzas.core.services.merchant_resolver import extract_acquirer_candidate


def test_extrae_comercio_tras_prefijo() -> None:
    assert extract_acquirer_candidate("TRANSBANK STARBUCKS 00123") == "STARBUCKS"
    assert extract_acquirer_candidate("WEBPAY *FARMACIA CRUZ VERDE") == "FARMACIA CRUZ VERDE"
    assert extract_acquirer_candidate("MERCADOPAGO RESTAURANTE X") == "RESTAURANTE X"


def test_sin_prefijo_o_insustancial_devuelve_none() -> None:
    assert (
        extract_acquirer_candidate("COMPRA LIDER") is None
    )  # LIDER no es adquirente... COMPRA sí?
    assert extract_acquirer_candidate("TRANSBANK 12") is None
    assert extract_acquirer_candidate("PAGO NORMAL SIN RUIDO") is None
