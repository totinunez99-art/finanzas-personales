# 24 — Validación Sprint 3 con datos reales (cartola Edwards)

> Estado: **EN CURSO** · Creado: 2026-07-17 · Rol: Lead QA / Auditor Técnico
> Regla de la fase: **cero funcionalidades nuevas, cero refactors** salvo bug crítico.
> Primero diagnóstico con evidencia; las soluciones se discuten después.

## 0. Correcciones de expectativa (antes de medir)

Declaradas ANTES de ver los resultados para que no parezcan excusas después:

1. **"Decisiones por IA" será 0.** El AiResolver es un stub por diseño (Sprint 3 excluyó
   IA explícitamente). No es un hallazgo: es el plan. Igual se reporta la columna.
2. **"Decisiones manuales" será 0 al inicio.** Solo existen tras usar el teach de
   comercios o corregir categorías. Se reporta su evolución durante la validación.
3. **"% correctas" exige ground truth que solo tiene el dueño.** El sistema puede medir
   *cobertura* (% resuelto) solo; *corrección* requiere que Tomás revise movimiento a
   movimiento. El protocolo incluye esa tabla de revisión (§3). Sin esa revisión, los %
   de corrección quedarán como "no calculable aún" — no se inventan.
4. **Deltas, semanas y anomalías dirán "sin base/insuficiente"** con un solo mes de
   datos (docs/23 §5). Verificar que lo digan honestamente ES parte de la validación.
5. **Flow es derivado:** su corrección es idéntica a la corrección de las categorías
   transfer (ADR-010 §6). Se mide la detección de internos, no la derivación.

## 1. Preflight (gates previos, lado dueño)

| Paso | Acción | Resultado |
|---|---|---|
| P1 | robocopy OneDrive → repo ejecución | ⬜ |
| P2 | git add/commit/push | ⬜ commit: |
| P3 | GitHub Actions verde (2 jobs) | ⬜ run #: |
| P4 | `docker compose up --build` (bootstrap aplica migración 0005) | ⬜ |
| P5 | Salud OK en Administración | ⬜ |

## 2. Protocolo de importación y pipeline

1. Importar la cartola real (Importar → PDF → contraseña → confirmar). Registrar:
   leídas / insertadas / duplicadas / descartadas / errores / warnings / confianza de
   extracción / cuadratura.
2. **Simular pipeline (dry-run) ANTES de ejecutar** y guardar el reporte: es la
   predicción auditable de lo que hará.
3. Ejecutar pipeline real. Comparar contra la simulación: deben coincidir (si difieren,
   bug crítico → detener validación).
4. Fuentes de auditoría: `GET /transactions`, `GET /stats/summary`, `GET /stats/insights`,
   `GET /stats/analytics`, `GET /metrics/summary`, reporte de `/resolution/run`,
   `domain_events` (correlation del batch).

## 3. Métricas — definición exacta (fórmula y fuente)

| Métrica | Fórmula | Fuente | ¿Calculable sin revisión del dueño? |
|---|---|---|---|
| Cobertura comercios | tx con merchant asignado / tx totales | transactions.merchant_source | Sí |
| Cobertura categorías | tx con category_id / tx totales | transactions.category_id | Sí |
| % sin clasificar | 1 − cobertura categorías | ídem | Sí |
| % internos / operacionales | tx flow=internal / total (y complemento) | transactions.flow | Sí |
| % comercios CORRECTOS | correctos según dueño / asignados | tabla de revisión §3.1 | **No — requiere revisión** |
| % categorías CORRECTAS | correctas según dueño / asignadas | tabla de revisión §3.1 | **No — requiere revisión** |
| % internos bien detectados | internos confirmados / internos reales según dueño | tabla de revisión §3.1 | **No — requiere revisión** |
| Decisiones por origen | conteo por decided_by / merchant_source | classification_decisions, transactions | Sí |

### 3.1 Tabla de revisión (ground truth)

Se genera con TODOS los movimientos del período: fecha, descripción, monto, comercio
asignado (y origen), categoría asignada (y regla), flow. Tomás marca ✔/✘ por columna y
anota el valor correcto donde falle. De ahí salen los % de corrección y la lista de
reglas/comercios a enseñar (§6 del encargo).

## 4. Resultados

*(se completa durante la validación — vacío hasta tener datos)*

## 5. Hallazgos e inconsistencias

*(ídem)*

## 6. Evaluación de reglas y plan de enseñanza

*(ídem)*

## 7. Deuda técnica priorizada

*(ídem — clasificación Crítica/Alta/Media/Baja)*

## 8. Retrospectiva Sprint 3

*(documento final, tras cerrar §4–§7)*
