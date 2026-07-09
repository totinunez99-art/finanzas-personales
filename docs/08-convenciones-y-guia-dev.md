# 08 — Convenciones del Proyecto y Guía para Desarrolladores

> Estado: **Aprobado** · Última actualización: 2026-07-06

## 1. Lenguaje y nombres

- Código, identificadores, commits y docstrings: **inglés**. Documentación de `/docs` y
  UI: **español**. (Mezclar idiomas en código envejece mal; la UI es para el usuario.)
- Python ≥3.12. Estilo: `ruff` (lint+format) con config en `pyproject.toml`. Tipado:
  `mypy --strict` en `core/` y `shared/`; gradual en el resto.
- Nombres de dominio canónicos (mismos en DB, código y docs): `transaction`, `account`,
  `category`, `import_batch`, `classification_rule`, `classification_decision`,
  `ai_call`, `domain_event`, `app_setting`, `exchange_rate`, `job_run`.

## 2. Reglas de arquitectura (verificadas por tooling, no por memoria)

- Dependencias entre capas según docs/02 §4, verificadas con `import-linter` en CI.
- Prohibido: SQL crudo fuera de repositorios; acceso a DB desde `dashboard/`; SDKs de
  LLM fuera de `ai/providers/`; `datetime.now()` sin timezone; `float` para dinero;
  `print()` (usar logger); atrapar `Exception` sin re-lanzar o registrar.
- Toda operación que muta datos financieros pasa por un service y emite el evento
  correspondiente en `domain_events` dentro de la misma transacción (ADR-009); regla
  verificada por test de convención.
- Config solo vía `shared/config.py` (pydantic-settings) y flags vía el catálogo tipado
  de `shared/flags.py` (docs/11). Ningún `os.environ` ni string mágico suelto.

## 3. Git y ciclo de cambio

- Trunk-based: `main` protegida, ramas cortas `feat/...`, `fix/...`, squash merge.
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`).
- Todo cambio no trivial: (1) si altera una decisión documentada → ADR nuevo o
  actualización del existente; (2) actualizar MASTER_PROJECT.md en el mismo PR.
- CI en cada push: ruff + mypy + import-linter + pytest. CI rojo = no merge.

## 4. Tests

- Framework: pytest. La DB de tests es Postgres real (testcontainers o compose), no
  SQLite: el proyecto depende de features de Postgres (`pg_trgm`, constraints, jsonb).
- Prioridad de cobertura (en orden): (1) parsers de conectores con fixtures reales
  anonimizados — cada bug de parser encontrado en producción se convierte en fixture;
  (2) deduplicación y reconciliación (property-based con hypothesis donde aplique);
  (3) pipeline de clasificación con LLM simulado (fake provider determinista);
  (4) services de reporte.
- Ningún test llama a un LLM real ni a IMAP real. Los adaptadores de proveedor se
  prueban con contract tests grabados (respx/vcr) marcados `@slow`, fuera del CI por defecto.

## 5. Definition of Done (por funcionalidad)

1. Análisis y diseño discutido (si es grande: ADR o sección de doc actualizada).
2. Código + tipos + tests pasando en CI.
3. Logs y manejo de errores en los caminos de fallo esperables.
4. Documentación tocada si cambió comportamiento o decisión.
5. MASTER_PROJECT.md actualizado (estado, pendientes, riesgos).

## 6. Setup de desarrollo (se completará al implementar)

```
git clone <repo> && cd finanzas-personales
cp .env.example .env        # completar secretos
docker compose up -d db
uv sync                     # deps (uv como gestor)
alembic upgrade head
pytest
```

## 7. Revisión crítica

- **Riesgo:** convenciones estrictas + un solo desarrollador = tentación de saltárselas.
  Por eso las reglas críticas viven en CI (ruff/mypy/import-linter), no en este documento.
- **Limitación:** `mypy --strict` global sería ideal pero frena el arranque; se estricta
  primero donde el costo de un bug es mayor (core, shared) y se expande.
