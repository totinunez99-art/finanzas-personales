"""Contrato de proveedor LLM (ADR-004). Fase 1: solo la interfaz.

Ningún módulo fuera de finanzas.ai.providers importa SDKs de proveedores.
Los adaptadores concretos (claude, openai, gemini, ollama) llegan con la
fase de clasificación.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class CompletionRequest:
    prompt_id: str
    prompt_version: str
    system: str
    user: str
    max_tokens: int = 1024
    temperature: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CompletionResponse:
    text: str
    model: str
    model_version: str | None
    tokens_in: int
    tokens_out: int
    latency_ms: int


class LLMProvider(Protocol):
    name: str

    def complete(self, request: CompletionRequest) -> CompletionResponse: ...
    def estimate_cost(self, request: CompletionRequest) -> Decimal: ...
