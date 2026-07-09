"""Import Wizard — servicio de importación de cartolas (docs/14).

Flujo en dos pasos, ambos deterministas sobre el mismo archivo:
1. preview():   detecta, parsea y describe QUÉ pasaría. No escribe dominio
                (única excepción: registra archivos no reconocidos).
2. import_statement(): parsea de nuevo y escribe, con dedup a nivel de DB.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from finanzas.connectors.statements.base import ImportResult
from finanzas.connectors.statements.pdf_utils import is_encrypted_pdf, password_opens
from finanzas.connectors.statements.registry import detect
from finanzas.core.models import (
    Account,
    ImportBatch,
    Transaction,
    UnrecognizedFile,
    User,
)
from finanzas.core.models.enums import EventType
from finanzas.core.services.dedup import compute_dedup_hash, normalize_description
from finanzas.core.services.events import emit
from finanzas.shared.errors import (
    AlreadyImportedError,
    NotFoundError,
    ParserError,
    UnsupportedFormatError,
)
from finanzas.shared.logging import get_logger

logger = get_logger("import_service")

PREVIEW_SAMPLE_SIZE = 20


PASSWORD_REQUIRED_MESSAGE = (
    "Este PDF está protegido. Ingresa su contraseña para continuar: se usa "
    "únicamente para leer el archivo y NUNCA se almacena ni se registra."
)


@dataclass(frozen=True)
class PreviewResult:
    recognized: bool
    message: str
    password_required: bool = False
    parser_name: str | None = None
    parser_version: str | None = None
    detected_format: str | None = None
    bank: str | None = None
    detection_reason: str | None = None
    total_rows: int = 0
    sample: list[dict[str, Any]] = field(default_factory=list)
    duplicates_in_db: int = 0
    file_already_imported: bool = False
    warnings: list[str] = field(default_factory=list)
    validation: list[dict[str, Any]] = field(default_factory=list)
    extraction_confidence: float | None = None


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _header_preview(content: bytes) -> str:
    try:
        text = content[:1000].decode("utf-8", errors="replace")
    except Exception:
        return ""
    return "\n".join(text.splitlines()[:3])[:500]


def _register_unrecognized(session: Session, user: User, filename: str, content: bytes) -> None:
    """Un formato desconocido es información para el próximo parser (docs/05)."""
    sha = _sha256(content)
    exists = session.execute(
        select(UnrecognizedFile).where(UnrecognizedFile.file_sha256 == sha)
    ).scalar_one_or_none()
    if exists is not None:
        return
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    session.add(
        UnrecognizedFile(
            user_id=user.id,
            filename=filename,
            file_sha256=sha,
            size_bytes=len(content),
            extension=extension[:16],
            header_preview=_header_preview(content),
        )
    )
    logger.info("unrecognized_file_registered", filename=filename, sha=sha[:12])


def _resolve_password(content: bytes, password: str | None) -> PreviewResult | None:
    """Fase A de detección (docs/18 §8): PDF cifrado sin clave o con clave errónea."""
    if not is_encrypted_pdf(content):
        return None
    if password is None or password == "":
        return PreviewResult(
            recognized=False, password_required=True, message=PASSWORD_REQUIRED_MESSAGE
        )
    if not password_opens(content, password):
        return PreviewResult(
            recognized=False,
            password_required=True,
            message="Contraseña incorrecta. Verifica e intenta de nuevo (no se almacena).",
        )
    return None


def _prepare_rows(account: Account, statement: ImportResult, sha: str) -> list[dict[str, Any]]:
    """RawTransaction → filas listas para insertar, con intra_day_seq y hash.

    intra_day_seq: correlativo por clave (fecha, monto, moneda, descripción)
    DENTRO del archivo, en orden de aparición (docs/03 §4).
    """
    seq_counter: dict[tuple[Any, ...], int] = {}
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(statement.transactions):
        currency = raw.currency or account.currency
        description_norm = normalize_description(raw.description_raw)
        key = (raw.posted_at, raw.amount, currency, description_norm)
        seq = seq_counter.get(key, 0)
        seq_counter[key] = seq + 1
        rows.append(
            {
                "posted_at": raw.posted_at,
                "occurred_at": raw.occurred_at,
                "amount": raw.amount,
                "currency": currency,
                "description_raw": raw.description_raw,
                "description_norm": description_norm,
                "merchant": raw.merchant_hint,
                "source_ref": f"{sha[:12]}:{raw.source_ref or index}",
                "installment_info": ({"raw": raw.installment_raw} if raw.installment_raw else None),
                "intra_day_seq": seq,
                "dedup_hash": compute_dedup_hash(
                    str(account.id), raw.posted_at, raw.amount, currency, description_norm, seq
                ),
            }
        )
    return rows


def _existing_hashes(session: Session, account_id: uuid.UUID, hashes: list[str]) -> set[str]:
    if not hashes:
        return set()
    found = session.execute(
        select(Transaction.dedup_hash).where(
            Transaction.account_id == account_id, Transaction.dedup_hash.in_(hashes)
        )
    ).scalars()
    return set(found)


def preview(
    session: Session,
    user: User,
    filename: str,
    content: bytes,
    account_id: uuid.UUID | None = None,
    password: str | None = None,
) -> PreviewResult:
    password_state = _resolve_password(content, password)
    if password_state is not None:
        return password_state

    detection = detect(filename, content, password)
    if detection is None:
        _register_unrecognized(session, user, filename, content)
        return PreviewResult(
            recognized=False,
            message=(
                "Este formato aún no es compatible. El archivo quedó registrado "
                "para facilitar la creación del parser correspondiente."
            ),
        )

    parser, info = detection
    statement = parser.parse(filename, content, password)  # ParserError sube claro
    _assert_validation(statement)
    sha = _sha256(content)

    duplicates = 0
    file_already_imported = False
    if account_id is not None:
        account = session.get(Account, account_id)
        if account is None or account.user_id != user.id:
            raise NotFoundError("Cuenta inexistente")
        rows = _prepare_rows(account, statement, sha)
        duplicates = len(_existing_hashes(session, account.id, [r["dedup_hash"] for r in rows]))
        file_already_imported = (
            session.execute(
                select(ImportBatch).where(
                    ImportBatch.account_id == account.id,
                    ImportBatch.file_sha256 == sha,
                    ImportBatch.status == "completed",
                )
            ).scalar_one_or_none()
            is not None
        )

    sample = [
        {
            "posted_at": raw.posted_at.isoformat(),
            "description": raw.description_raw,
            "amount": str(raw.amount),
            "currency": raw.currency,
        }
        for raw in statement.transactions[:PREVIEW_SAMPLE_SIZE]
    ]
    return PreviewResult(
        recognized=True,
        message="Archivo reconocido",
        parser_name=parser.name,
        parser_version=statement.parser_version,
        detected_format=statement.detected_format,
        bank=parser.bank,
        detection_reason=info.reason,
        total_rows=len(statement.transactions),
        sample=sample,
        duplicates_in_db=duplicates,
        file_already_imported=file_already_imported,
        warnings=list(statement.warnings),
        validation=statement.validation.to_payload()["checks"],
        extraction_confidence=statement.extraction_confidence,
    )


def _assert_validation(statement: ImportResult) -> None:
    """Defensa en profundidad: un parser DEBE lanzar ante validación dura fallida;
    si no lo hizo, el núcleo bloquea igual (nada se importa con validación roja)."""
    if statement.validation.passed:
        return
    failed = [c.name for c in statement.validation.checks if not c.passed]
    raise ParserError(
        f"Validación de integridad fallida ({', '.join(failed)}). "
        "La importación se cancela: ningún movimiento fue insertado."
    )


def import_statement(
    session: Session,
    user: User,
    account_id: uuid.UUID,
    filename: str,
    content: bytes,
    password: str | None = None,
) -> ImportBatch:
    account = session.get(Account, account_id)
    if account is None or account.user_id != user.id:
        raise NotFoundError("Cuenta inexistente")

    password_state = _resolve_password(content, password)
    if password_state is not None:
        raise UnsupportedFormatError(password_state.message)

    detection = detect(filename, content, password)
    if detection is None:
        _register_unrecognized(session, user, filename, content)
        raise UnsupportedFormatError("Este formato aún no es compatible.")
    parser, _info = detection

    sha = _sha256(content)
    previous = session.execute(
        select(ImportBatch).where(
            ImportBatch.account_id == account.id,
            ImportBatch.file_sha256 == sha,
            ImportBatch.status == "completed",
        )
    ).scalar_one_or_none()
    if previous is not None:
        raise AlreadyImportedError(
            f"Este archivo ya fue importado el {previous.created_at:%Y-%m-%d} "
            f"({previous.rows_inserted} movimientos). Reimportarlo no tiene efecto."
        )

    statement = parser.parse(filename, content, password)
    _assert_validation(statement)
    rows = _prepare_rows(account, statement, sha)
    existing = _existing_hashes(session, account.id, [r["dedup_hash"] for r in rows])

    batch = ImportBatch(
        user_id=user.id,
        account_id=account.id,
        connector=parser.name,
        filename=filename[:255],
        file_sha256=sha,
        period_start=statement.period_start,
        period_end=statement.period_end,
        rows_read=len(rows),
        status="pending",
        parser_version=statement.parser_version,
        detected_format=statement.detected_format,
        validation=statement.validation.to_payload(),
        opening_balance=statement.opening_balance,
        closing_balance=statement.closing_balance,
        extraction_confidence=Decimal(str(statement.extraction_confidence)),
    )
    session.add(batch)
    session.flush()

    inserted = 0
    duplicated = 0
    for row in rows:
        if row["dedup_hash"] in existing:
            duplicated += 1
            continue
        transaction = Transaction(
            user_id=user.id,
            account_id=account.id,
            status="confirmed",  # cartola = fuente de verdad (ADR-003)
            source="statement",
            import_batch_id=batch.id,
            **row,
        )
        session.add(transaction)
        session.flush()
        emit(
            session,
            EventType.TRANSACTION_IMPORTED,
            entity="transaction",
            entity_id=transaction.id,
            payload={"batch": str(batch.id), "source_ref": row["source_ref"]},
        )
        inserted += 1

    batch.rows_inserted = inserted
    batch.rows_duplicated = duplicated
    batch.status = "warning" if statement.warnings else "completed"
    if statement.warnings:
        batch.error_detail = "; ".join(statement.warnings)[:2000]

    emit(
        session,
        EventType.BATCH_COMPLETED,
        entity="import_batch",
        entity_id=batch.id,
        payload={
            "connector": parser.name,
            "read": batch.rows_read,
            "inserted": inserted,
            "duplicated": duplicated,
        },
    )
    logger.info(
        "statement_imported",
        batch=str(batch.id),
        connector=parser.name,
        read=batch.rows_read,
        inserted=inserted,
        duplicated=duplicated,
    )
    session.flush()
    session.refresh(batch)  # carga created_at (server_default) antes de que lo lea la API
    return batch
