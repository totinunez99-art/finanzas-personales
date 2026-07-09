"""Normalización canónica y hash de deduplicación (docs/03 §4).

La normalización BASE es común a todas las fuentes; cada parser bancario podrá
aplicar limpieza adicional específica (nº de operación variable, etc.) ANTES de
llamar aquí. El hash es la identidad de la transacción a nivel de DB.
"""

import hashlib
import unicodedata
from datetime import date
from decimal import Decimal


def normalize_description(raw: str) -> str:
    """Mayúsculas, sin tildes, espacios colapsados. Determinista y testeada."""
    text = unicodedata.normalize("NFKD", raw)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = " ".join(text.upper().split())
    return text


def compute_dedup_hash(
    account_id: str,
    posted_at: date,
    amount: Decimal,
    currency: str,
    description_norm: str,
    intra_day_seq: int = 0,
) -> str:
    """sha256 sobre campos canónicos. El monto se serializa sin ceros espurios
    (Decimal("10.50") y Decimal("10.5000") producen el mismo hash)."""
    canonical_amount = format(amount.normalize(), "f")
    payload = "|".join(
        [
            account_id,
            posted_at.isoformat(),
            canonical_amount,
            currency.upper(),
            description_norm,
            str(intra_day_seq),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
