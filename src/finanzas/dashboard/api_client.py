"""Cliente HTTP hacia la API. Única vía de datos del dashboard (ADR-006).

Nota import-linter: este módulo NO importa finanzas.core ni finanzas.shared.config
para respetar la frontera; la URL llega por variable de entorno simple.
Nunca lanza: devuelve (datos, error) y la UI decide cómo mostrarlo.
"""

import os
from typing import Any

import requests

_TIMEOUT_SECONDS = 30

Result = tuple[Any | None, str | None]


def api_base_url() -> str:
    return os.environ.get("API_BASE_URL", "http://localhost:8000")


def _handle(response: requests.Response) -> Result:
    if response.ok:
        return response.json(), None
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    return None, f"{response.status_code}: {detail}"


def get_json(path: str, params: dict[str, Any] | None = None) -> Result:
    try:
        return _handle(requests.get(f"{api_base_url()}{path}", params=params, timeout=5))
    except requests.RequestException as exc:
        return None, str(exc)


def post_json(path: str, payload: dict[str, Any]) -> Result:
    try:
        return _handle(requests.post(f"{api_base_url()}{path}", json=payload, timeout=10))
    except requests.RequestException as exc:
        return None, str(exc)


def post_file(path: str, filename: str, content: bytes, data: dict[str, str]) -> Result:
    try:
        response = requests.post(
            f"{api_base_url()}{path}",
            files={"file": (filename, content)},
            data=data,
            timeout=_TIMEOUT_SECONDS,
        )
        return _handle(response)
    except requests.RequestException as exc:
        return None, str(exc)
