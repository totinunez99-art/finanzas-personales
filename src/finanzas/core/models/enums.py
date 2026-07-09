"""Enumeraciones del dominio (docs/03).

Se almacenan como VARCHAR + CHECK constraint (no enums nativos de PG):
evolucionar un enum nativo exige DDL especial; un CHECK se reemplaza en una
migración trivial. La validación fuerte adicional ocurre en la capa Pydantic.
"""

import enum


class AccountType(enum.StrEnum):
    CHECKING = "checking"
    CREDIT_CARD = "credit_card"
    SAVINGS = "savings"
    CREDIT_LINE = "credit_line"
    CASH = "cash"


class CategoryKind(enum.StrEnum):
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


class TransactionStatus(enum.StrEnum):
    PROVISIONAL = "provisional"  # nacida de email, aún sin cartola (docs/03 §5)
    CONFIRMED = "confirmed"      # nacida de cartola
    RECONCILED = "reconciled"    # email confirmado por cartola
    ORPHAN = "orphan"            # email sin match tras llegar la cartola del período


class TransactionSource(enum.StrEnum):
    EMAIL = "email"
    STATEMENT = "statement"
    MANUAL = "manual"


class DecidedBy(enum.StrEnum):
    RULE = "rule"
    AI = "ai"
    USER = "user"


class RuleMatcherType(enum.StrEnum):
    MERCHANT_EXACT = "merchant_exact"
    DESCRIPTION_CONTAINS = "description_contains"
    REGEX = "regex"


class RuleOrigin(enum.StrEnum):
    SYSTEM_SEED = "system_seed"
    USER = "user"
    PROMOTED = "promoted"


class ImportBatchStatus(enum.StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    WARNING = "warning"   # p.ej. cuadratura de saldos no cierra (docs/05 §3)
    FAILED = "failed"


class JobStatus(enum.StrEnum):
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"


class AiCallStatus(enum.StrEnum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


class EventType(enum.StrEnum):
    """Catálogo cerrado de eventos de dominio (ADR-009). Strings libres prohibidos."""

    TRANSACTION_IMPORTED = "transaction.imported"
    TRANSACTION_NORMALIZED = "transaction.normalized"
    TRANSACTION_CLASSIFIED = "transaction.classified"
    TRANSACTION_CORRECTED = "transaction.corrected"
    TRANSACTION_RECONCILED = "transaction.reconciled"
    TRANSACTION_DEDUPLICATED = "transaction.deduplicated"
    RULE_CREATED = "rule.created"
    RULE_PROMOTED = "rule.promoted"
    BATCH_COMPLETED = "batch.completed"
    BATCH_FAILED = "batch.failed"
    BACKUP_COMPLETED = "backup.completed"
    JOB_FAILED = "job.failed"
    SETTINGS_CHANGED = "settings.changed"
    AI_BUDGET_EXCEEDED = "ai.budget_exceeded"


def values(e: type[enum.StrEnum]) -> list[str]:
    """Valores de un enum, para CHECK constraints en los modelos."""
    return [member.value for member in e]
