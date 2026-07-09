# ADR-008 — Auditoría y versionado de decisiones de IA

Fecha: 2026-07-06 · Estado: **Aceptado** (origen: revisión CTO)

## Contexto

Requisito: toda decisión de IA debe ser auditable, comparable entre modelos y
reprocesable. El diseño previo capturaba parte (tabla `ai_usage` agregada por llamada;
`classified_by`/`confidence` en la transacción) pero: no versionaba prompts, no guardaba
la respuesta cruda, y el historial de decisiones por transacción no existía — solo el
estado final y una tabla de feedback separada.

## Alternativas

1. Ampliar `ai_usage` con columnas de auditoría: insuficiente — una llamada batch cubre
   30 transacciones; la auditoría se necesita **por decisión**.
2. Guardar historial en jsonb dentro de `transactions`: anti-patrón; imposible consultar
   ("accuracy del modelo X en mayo") sin destripar json por fila.
3. **(Elegida)** Dos tablas normalizadas + prompts versionados en git, reemplazando
   `ai_usage` y `classification_feedback` para no duplicar responsabilidades.

## Decisión

**Prompts versionados en código:** cada prompt vive en `ai/prompts/` con identificador y
versión explícitos (`PROMPT_ID="classification"`, `PROMPT_VERSION="1.2.0"`) y hash
sha256 del texto calculado en runtime. Cambiar un prompt = bump de versión en el mismo PR.

**Tabla `ai_calls`** — una fila por llamada a un LLM (reemplaza a `ai_usage`):
`id`, `provider`, `model` (solicitado), `model_version` (la que reporta la API en la
respuesta), `prompt_id`, `prompt_version`, `prompt_sha256`, `task`, `tokens_in`,
`tokens_out`, `cost_estimate`, `latency_ms`, `status (ok|error|timeout)`, `error_detail`,
`raw_response jsonb`, `created_at`.

**Tabla `classification_decisions`** — una fila por decisión sobre una transacción
(reemplaza a `classification_feedback`):
`id`, `user_id`, `transaction_id`, `decided_by (rule|ai|user)`, `rule_id fk null`,
`ai_call_id fk null`, `category_id`, `merchant`, `confidence null`, `is_current bool`,
`superseded_by fk null`, `created_at`.

- El historial completo vive aquí; `transactions.category_id/classified_by/confidence`
  es solo el estado actual denormalizado (sincronizado por el service, único escritor).
- Una **corrección manual es una decisión** `decided_by=user` que marca `is_current=false`
  y `superseded_by` en la anterior. El aprendizaje (few-shot, promoción a reglas)
  consulta decisiones de usuario — la tabla de feedback separada desaparece porque sería
  la misma información dos veces.

## Qué habilita

- Auditoría: "¿por qué esta transacción es 'Supermercado'?" → cadena completa de decisiones.
- Comparación entre modelos: accuracy/costo por (provider, model, prompt_version) con SQL simple.
- Reprocesamiento: reclasificar un lote con un modelo nuevo crea decisiones nuevas sin
  perder las anteriores; nunca se auto-supersede una decisión de usuario (regla dura:
  una decisión `ai` jamás reemplaza a una `user`).

## Consecuencias y revisión crítica

- (+) Evaluación de IA (docs/04 §7) pasa de diseño aspiracional a queries concretas.
- (−) `raw_response` acumula texto: volumen estimado trivial (<50 MB/año); retención
  configurable 12 meses para lo crudo, las filas se conservan.
- (−) Doble escritura (decisión + denormalizado en transaction) exige que SOLO el
  service escriba ambas en la misma transacción DB — regla verificada en revisión de código.
- Caso borde: reclasificación batch con modelo nuevo en modo comparación no debe tocar
  `is_current` (flag `dry_run` en el service; decisiones quedan marcadas `task=eval`).
