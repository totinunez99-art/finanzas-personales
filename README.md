# Finanzas Personales

Copiloto financiero personal. Documentación en [`docs/`](docs/); estado del proyecto en
[`MASTER_PROJECT.md`](MASTER_PROJECT.md).

## Arranque rápido (Docker) — un solo comando

```bash
cp .env.example .env      # completar POSTGRES_PASSWORD y DATABASE_URL
docker compose up --build
```

Eso es todo: el servicio `bootstrap` espera la DB, aplica migraciones y crea el
usuario por defecto ANTES de que arranquen API y worker. Idempotente en cada arranque.

- API: http://localhost:8000/health
- Dashboard: http://localhost:8501

Demo Mode (datos 100% ficticios, opcional):

```bash
docker compose run --rm demo
```

Luego en el dashboard: **Movimientos** (datos demo) e **Importar** (arrastra
`scripts/demo_data/demo_agosto_para_wizard.csv` para probar el wizard completo).

Guía completa y solución de problemas: [docs/15](docs/15-instalacion-y-troubleshooting.md).
Checklist de validación del Sprint 1: [docs/16](docs/16-validacion-sprint-1.md).

## Desarrollo local (sin Docker, salvo la DB)

```bash
docker compose up -d db
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py                            # usuario por defecto
uvicorn finanzas.api.main:app --reload
```

## Calidad (mismos checks que la CI)

```bash
ruff check . && ruff format --check .
mypy
lint-imports
pytest tests/unit
TEST_DATABASE_URL=postgresql+psycopg://... pytest -m integration   # requiere PG
```
