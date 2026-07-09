# ADR-009 — Event log ligero unificado (`domain_events`), desde el MVP

Fecha: 2026-07-06 · Estado: **Aceptado** (origen: revisión CTO)

## Contexto

Se pide un historial cronológico de eventos importantes (importado, normalizado,
clasificado, corregido, reconciliado, deduplicado, aprendizaje) para auditoría y
análisis. No Event Sourcing. El diseño previo ya tenía `audit_log` con propósito
solapado — mantener ambos sería duplicar la misma responsabilidad en dos tablas.

## Alternativas

1. `audit_log` + event log separados: dos tablas append-only con el mismo rol y criterios
   difusos de qué va dónde. Rechazada por duplicación.
2. Event Sourcing (estado derivado de eventos): rechazada explícitamente — reescribe la
   arquitectura entera por un beneficio que nadie pidió; el estado vive en las tablas de dominio.
3. Broker de eventos (Redis streams, etc.): infraestructura sin consumidores que la justifiquen.
4. **(Elegida)** Tabla única `domain_events`, append-only, que **absorbe y reemplaza** a `audit_log`.

## Decisión

Tabla `domain_events`:
`id`, `occurred_at`, `event_type`, `entity`, `entity_id`, `actor (system|user|job:<name>)`,
`correlation_id` (une todos los eventos de un mismo batch/job), `payload jsonb` (mínimo:
referencias e ids, nunca copias de datos), `created_at`. Índices por (entity, entity_id) y (event_type, occurred_at).

- **Catálogo cerrado de eventos versionado en código** (enum): `transaction.imported`,
  `.normalized`, `.classified`, `.corrected`, `.reconciled`, `.deduplicated`,
  `rule.created`, `rule.promoted`, `batch.completed`, `batch.failed`, `backup.completed`,
  `job.failed`, `settings.changed`, `ai.budget_exceeded`. Strings libres prohibidos.
- **Emisión síncrona en la misma transacción DB** que la mutación (helper `emit()` en los
  services): garantiza evento ⇔ cambio, sin brokers ni riesgo de eventos perdidos/fantasma.
- **Regla dura de no-dependencia:** los eventos NO son load-bearing. Las métricas se
  calculan de las tablas de dominio (docs/10 §3); ningún proceso reconstruye estado desde
  eventos. Un bug en la emisión no corrompe datos, solo empobrece la traza.

## Análisis costo/beneficio (¿por qué desde el MVP?)

- Costo hoy: 1 tabla + 1 helper + una línea por mutación en cada service (~horas).
- Costo de retrofit: instrumentar a posteriori todos los services ya escritos y perder
  la historia del período más delicado (los primeros meses, cuando la reconciliación se depura).
- Volumen: <100k filas/año a escala personal — despreciable.
- Beneficio concreto: depurar reconciliación ("¿qué le pasó a esta transacción?" →
  timeline completa), auditoría exigida por el CTO, y base para una vista cronológica en
  el dashboard sin trabajo adicional.

**Recomendación: sí, desde el MVP.** Es de las pocas piezas donde "diseñar desde el
inicio" es más barato que diferir.

## Consecuencias

- (+) Una sola fuente de trazas de negocio; `audit_log` desaparece del modelo (docs/03 actualizado).
- (−) Disciplina de emisión en cada service nuevo — se protege con test de convención
  (cada método público de service que muta datos debe emitir; verificado por test genérico).
- (−) `payload` tentará a copiar datos completos; la regla "referencias, no copias" se
  vigila en revisión de código.
- Retención: particionar o archivar >24 meses si alguna vez molesta (improbable).
