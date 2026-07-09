"""Import Wizard vía HTTP (docs/14).

POST /imports/preview  → qué pasaría (detección, muestra, duplicados). No escribe dominio.
POST /imports          → importa con dedup. Requiere el mismo archivo + cuenta.
GET  /imports          → batches recientes (estado de importación en el dashboard).
"""

import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from finanzas.api.deps import get_current_user, get_db
from finanzas.core.models import ImportBatch, User
from finanzas.core.services import import_service
from finanzas.shared.errors import (
    AlreadyImportedError,
    NotFoundError,
    ParserError,
    UnsupportedFormatError,
)

router = APIRouter(prefix="/imports", tags=["imports"])

MAX_FILE_BYTES = 10 * 1024 * 1024  # una cartola jamás pesa más que esto


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Archivo vacío")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx. 10 MB)")
    return file.filename or "archivo", content


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field} inválido: {value!r}") from exc


@router.post("/preview")
async def preview(
    file: UploadFile = File(...),
    account_id: str | None = Form(default=None),
    password: str | None = Form(default=None),  # solo lectura del PDF; jamás se persiste
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    filename, content = await _read_upload(file)
    parsed_account_id = _parse_uuid(account_id, "account_id") if account_id else None
    try:
        result = import_service.preview(
            db, user, filename, content, parsed_account_id, password=password
        )
    except ParserError as exc:
        # Reconocido pero inválido: error comprensible, no un 500.
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    return asdict(result)


@router.post("", status_code=201)
async def confirm_import(
    file: UploadFile = File(...),
    account_id: str = Form(...),
    password: str | None = Form(default=None),  # solo lectura del PDF; jamás se persiste
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    filename, content = await _read_upload(file)
    try:
        batch = import_service.import_statement(
            db,
            user,
            _parse_uuid(account_id, "account_id"),
            filename,
            content,
            password=password,
        )
    except ParserError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=415, detail=exc.message) from exc
    except AlreadyImportedError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    return _batch_to_dict(batch)


def _batch_to_dict(batch: ImportBatch) -> dict[str, Any]:
    return {
        "id": str(batch.id),
        "connector": batch.connector,
        "filename": batch.filename,
        "status": batch.status,
        "parser_version": batch.parser_version,
        "detected_format": batch.detected_format,
        "validation": batch.validation,
        "extraction_confidence": (
            str(batch.extraction_confidence) if batch.extraction_confidence is not None else None
        ),
        "rows_read": batch.rows_read,
        "rows_inserted": batch.rows_inserted,
        "rows_duplicated": batch.rows_duplicated,
        "rows_failed": batch.rows_failed,
        "period_start": batch.period_start.isoformat() if batch.period_start else None,
        "period_end": batch.period_end.isoformat() if batch.period_end else None,
        "error_detail": batch.error_detail,
        "created_at": batch.created_at.isoformat(),
    }


@router.get("")
def list_imports(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    batches = db.execute(
        select(ImportBatch)
        .where(ImportBatch.user_id == user.id)
        .order_by(ImportBatch.created_at.desc())
        .limit(min(limit, 100))
    ).scalars()
    return [_batch_to_dict(b) for b in batches]
