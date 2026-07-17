# 16 — Checklist de Validación del Sprint 1

> Estado: **En ejecución** · Creado: 2026-07-06
> El Sprint 1 se cierra cuando TODOS los ítems estén marcados. Ejecutor: Tomás.
> Regla: un ítem que falla se anota con su error exacto en §5 antes de continuar.

## Fase A — Infraestructura (una vez)

- [ ] A1. Push a GitHub → **CI completa en verde** (lint, tipos, import-linter, unit, golden, integración con PG real).
- [ ] A2. `docker compose up --build` (ÚNICO comando): `bootstrap` termina "Bootstrap OK" y recién entonces arrancan api y worker, sin errores.
- [ ] A3. http://localhost:8000/health responde `db: true` y `migration: "0002"`.
- [ ] A4. Dashboard (página principal) muestra API/DB en verde y, tras ~5 min, el job `heartbeat` con estado ok (sin errores `relation does not exist` en `docker compose logs worker`).
- [ ] A5. Usuario por defecto creado automáticamente (visible en logs de bootstrap; la página Importar no muestra error 503).
- [ ] A6. `docker compose down` + `docker compose up` (SIN -v): re-arranque idempotente, bootstrap termina en segundos sin re-migrar.

## Fase B — Flujo completo con datos FICTICIOS (Demo Mode)

- [ ] B1. `docker compose run --rm demo` → junio: 14 insertados / 0 duplicados; julio: 9 insertados / **1 duplicado omitido** (prueba de dedup entre archivos).
- [ ] B2. Correr `docker compose run --rm demo` de nuevo → ambos archivos reportan "ya estaba importado" (idempotencia).
- [ ] B3. Página **Movimientos**: contador = 23, listado con fecha/descripción/monto/tipo, y 2 importaciones en estado `completed`.
- [ ] B4. Página **Importar**: arrastrar `scripts/demo_data/demo_agosto_para_wizard.csv` → detección `generic`, vista previa con 8 movimientos, 0 duplicados → **Confirmar** → éxito → Movimientos = 31.
- [ ] B5. Volver a arrastrar el MISMO archivo → la vista previa avisa "archivo ya importado" y confirmar está bloqueado (o responde 409).
- [ ] B6. Arrastrar un CSV cualquiera con otro encabezado → mensaje "Este formato aún no es compatible" SIN error del sistema.
- [ ] B7. Cancelación: subir un archivo, ver la vista previa y cerrar la página SIN confirmar → Movimientos no cambia.

## Fase C — Flujo con DATOS REALES (criterio de éxito del sprint)

- [ ] C1. Crear cuenta real (ej: "Cuenta Corriente Banco de Chile", CLP).
- [ ] C2. Convertir una cartola real al formato puente (docs/14 §4) y guardarla local (fuera del repo).
- [ ] C3. Importarla vía wizard: vista previa correcta (fechas, montos, signos) → confirmar.
- [ ] C4. Verificar en Movimientos contra la cartola original: mismo número de movimientos, mismos montos, cargos negativos y abonos positivos.
- [ ] C5. Reimportar la misma cartola → rechazada por duplicada.
- [ ] C6. Repetir C2-C5 con un segundo mes → solo entra lo nuevo.
- [ ] C7. **Repetir el proceso completo una segunda vez en otro día** (criterio: "repetir el proceso con éxito").

## Fase D — Cierre

- [ ] D1. Errores encontrados anotados en §5 y corregidos (cada bug real → caso golden, docs/13).
- [ ] D2. Cartolas reales del Banco de Chile descargadas a `golden/originals/statements/bancochile/` (desbloquea el conector real del Sprint 2).
- [ ] D3. MASTER_PROJECT actualizado: Sprint 1 CERRADO, con fecha.

## §5 — Hallazgos durante la validación

| # | Fecha | Ítem | Error observado (texto exacto) | Resolución |
|---|---|---|---|---|
| 1 | 2026-07-06 | A2/A4 | `psycopg.errors.UndefinedTable: relation "job_runs" does not exist` — worker arrancó antes de que api terminara las migraciones (`service_started` no espera comandos internos) | Rediseño estructural del arranque: servicio `bootstrap` one-shot (espera DB → migra → seed) con `service_completed_successfully` como condición de api/worker; guardas `wait_for_db`+`assert_migrated` en worker y scripts; `scripts/` faltaba en la imagen Docker (2º bug de instalación encontrado en la misma revisión). Ver MASTER_PROJECT sesión 8 |
| 2 | 2026-07-08 | B3 | MENOR (cosmético): home muestra "Última importación: demo_junio.csv" en vez de julio — ambos batches del script demo comparten transacción DB y `now()` es idéntico → orden por `created_at` ambiguo. No ocurre en uso real (un archivo por vez) | Pendiente (baja prioridad): usar `clock_timestamp()` como default o desempatar el orden. Registrado; no bloquea el gate |
| 3 | 2026-07-08 | B3 | AVISO de deprecación Streamlit: `use_container_width` se elimina a fines de 2025 → migrar a `width='stretch'` | Pendiente (cosmético): cambio de una línea en components.py y páginas, próximo commit |
