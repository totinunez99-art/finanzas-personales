"""Modelos del dominio. Importar desde aquí garantiza metadata completa para Alembic."""

from finanzas.core.models.base import Base
from finanzas.core.models.catalog import Account, Category
from finanzas.core.models.classification import (
    AiCall,
    ClassificationDecision,
    ClassificationRule,
    MerchantRule,
)
from finanzas.core.models.operational import (
    AppSetting,
    DomainEvent,
    ExchangeRate,
    ImportBatch,
    JobRun,
    UnparsedEmail,
    UnrecognizedFile,
)
from finanzas.core.models.transaction import Transaction
from finanzas.core.models.user import User

__all__ = [
    "Account",
    "AiCall",
    "AppSetting",
    "Base",
    "Category",
    "ClassificationDecision",
    "ClassificationRule",
    "DomainEvent",
    "ExchangeRate",
    "ImportBatch",
    "JobRun",
    "MerchantRule",
    "Transaction",
    "UnparsedEmail",
    "UnrecognizedFile",
    "User",
]
