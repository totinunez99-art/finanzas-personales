# 19 — Quality Gates

> Estado: **Vivo** · Creado: 2026-07-08 (regla de desarrollo, sesión 12)
> **Regla:** ningún bloque nuevo se construye sobre una base no validada. Un gate se
> cierra solo con evidencia (CI verde, ejecución real registrada), nunca por optimismo.
> Valida: Tomás en su PC + CI. La fecha de validación se registra aquí con el resultado.

## Estados posibles

`NO INICIADO` → `EN DESARROLLO` → `EN VALIDACIÓN` → `✅ VALIDADO (fecha)` / `❌ RECHAZADO (motivo)`
`NO PLANIFICADO`: decisión explícita de no construir (con referencia al análisis).

## Tabla de gates

| # | Gate | Objetivo | Criterio de aceptación | Estado | Validado |
|---|---|---|---|---|---|
| G1 | **Infraestructura** | Instalación limpia operativa con un comando | CI completa verde (lint+tipos+fronteras+unit+golden+integración PG) **y** `docker compose up --build` desde cero: bootstrap OK, /health con migración 0003, dashboard arriba, heartbeat ok (docs/16 fase A completa) | **EN VALIDACIÓN** | — |
| G2 | **Importación CSV** | Flujo completo usable: preview→confirmar→dedup→ver movimientos | docs/16 fases B (demo, números exactos) y C (cartola real convertida, 2 meses, re-importación rechazada) completas | **EN VALIDACIÓN** | — |
| G3 | **Edwards PDF** | Importar cartola Edwards nativa (PDF cifrado) sin conversión manual | Casos golden reales anonimizados + complementos sintéticos pasando en CI; regresión local contra PDF real OK; cuadratura dual (texto+metadata CVQT) exacta; contraseña pedida y jamás persistida; importación end-to-end desde el dashboard | **EN DESARROLLO** (bloque 1/3 listo: contratos, password, trazabilidad — 39/39 tests; bloques 2-3 esperan cierre de G1+G2) | — |
| G4 | **Dashboard financiero** | Métricas del período + búsqueda/filtros útiles a diario | Stats correctas contra datos reales importados (ingresos/gastos/neto por moneda), filtros verificados (docs/16 + inspección manual de Tomás), sin errores de conexión | **EN VALIDACIÓN** | — |
| G5 | **IA de clasificación** | Clasificación automática auditable con corrección barata | Pipeline reglas→LLM en modo sombra 2 semanas; precisión ≥90% en sombra antes de auto-asignar; costo dentro de presupuesto; evaluación semanal operando (docs/04 §7-8) | **NO INICIADO** (diseño completo en docs/04; bloqueado por G3 + proveedor LLM sin decidir) | — |
| G6 | **OCR** | Leer documentos sin texto embebido | — | **NO PLANIFICADO**: docs/18 §1 demostró que la cartola Edwards es texto nativo; no existe caso de uso actual. Se reevalúa solo si aparece un documento real escaneado | — |
| G7 | **Presupuestos** | Definir y monitorear presupuestos por categoría | Requiere clasificación estable (G5) + ≥2 meses de datos clasificados; criterios se definirán al diseñar la fase (roadmap docs/01 Fase 3+) | **NO INICIADO** | — |
| G8 | **Inversiones** | Registro y valorización de inversiones (UF/USD) | Requiere job de tasas de cambio operativo + diseño de dominio propio (docs/01 Fase 4) | **NO INICIADO** | — |

## Gate activo: cierre del Bloque 1 (G1 + G2)

Checklist ejecutable (el detalle numérico vive en docs/16; aquí el resumen del gate):

1. ☐ Repo git creado en el clon de ejecución, push a GitHub (privado).
   Nota sesión 12: la carpeta OneDrive NO soporta git (locks del filesystem — verificado);
   el repo vive en `C:\Finanzas personales\Finanzas personales`.
2. ☐ CI completa verde en el primer push (o hallazgos corregidos y re-push verde).
3. ☐ Instalación limpia: `docker compose down -v && docker compose up --build` →
   bootstrap "OK", `/health` reporta `migration: "0003"`.
4. ☐ docs/16 fase A (A2-A6) completa.
5. ☐ docs/16 fase B completa (demo con números exactos + wizard manual + cancelación).
6. ☐ Preview e importación CSV desde el dashboard con archivo real convertido (fase C mínima: C1-C5).
7. ☐ Hallazgos anotados en docs/16 §5; los que sean bugs → caso golden antes del fix.
8. ☐ Estados G1/G2 actualizados aquí con fecha y evidencia (texto breve: qué se corrió, resultado).

**Al cerrar G1+G2 → comienza Bloque 2 de G3 (anonimización + casos golden Edwards).**

## Registro de validaciones

| Fecha | Gate | Resultado | Evidencia |
|---|---|---|---|
| 2026-07-08 | G3 (parcial, bloque 1) | 39/39 tests unit+golden en sandbox (Python 3.10+shim; no autoritativo) + py_compile limpio | Sesión 12; CI pendiente |
| 2026-07-08 | G1/G2 (primer push) | **CI ROJA** — 2 jobs fallidos. Causas raíz: (1) `ruff format` nunca ejecutado (20 archivos) + 28 errores lint (25 = falso positivo B008/FastAPI, resuelto con `extend-immutable-calls`); (2) bug real en `stats_summary`: montos `"1000000.0000"` con ceros espurios de Numeric(18,4) — detectado reproduciendo la integración en sandbox con Postgres embebido (pgserver) ANTES de la CI | Sesión 12; fix `_fmt_amount` canónico |
| 2026-07-08 | G1/G2 (pre re-push) | Pipeline local completo VERDE: ruff check+format ✓ · mypy 58 archivos ✓ · import-linter 2/2 contratos ✓ · unit+golden 39/39 ✓ · integración 7/7 con PG embebido (única omisión: pg_trgm, no disponible en sandbox; la imagen postgres:16 de CI sí lo trae) | Sesión 12; autoritativo = CI del re-push |
