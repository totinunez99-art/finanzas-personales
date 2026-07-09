# 04 — Estrategia de IA y Motor de Clasificación

> Estado: **Aprobado** · Última actualización: 2026-07-06 (revisión CTO)
> Decisiones formales: [ADR-004](adr/ADR-004-abstraccion-llm.md), [ADR-007](adr/ADR-007-chromadb-diferido.md), [ADR-008](adr/ADR-008-auditoria-decisiones-ia.md)

## 1. Principio: la IA es un empleado auditable, no un oráculo

Toda decisión queda registrada con quién la tomó, con qué modelo, prompt, confianza y
costo (ADR-008), y es corregible. El sistema funciona con la IA apagada
(`ai.enabled=false`, docs/11): reglas + revisión manual. La IA reduce fricción; no es
dependencia estructural.

## 2. Capa de abstracción multi-proveedor

Interfaz única en `ai/providers/base.py`:

```python
class LLMProvider(Protocol):
    name: str
    def complete(self, request: CompletionRequest) -> CompletionResponse: ...
    def estimate_cost(self, request: CompletionRequest) -> Decimal: ...
```

- `CompletionRequest/Response` son tipos propios (Pydantic). Ningún módulo fuera de
  `ai/providers/` importa SDKs de proveedores.
- Selección por configuración (docs/11): `.env` define proveedor por defecto y cadena de
  fallback (ej: `ollama → claude`); `ai.provider_override` permite forzar uno en runtime.
- **Sin framework** (LangChain, etc.): superficie usada mínima; justificación en ADR-004.
- Toda llamada se registra en **`ai_calls`** (proveedor, modelo, versión reportada,
  prompt_id+versión+sha, tokens, costo, latencia, respuesta cruda — ADR-008).
- Prompts versionados en `ai/prompts/` con `PROMPT_ID` y `PROMPT_VERSION` explícitos;
  cambiar un prompt = bump de versión en el mismo PR.

## 3. Motor de reglas deterministas (primera línea, antes de cualquier IA)

Tabla `classification_rules` (docs/03). Diseño completo:

- **Tipos de matcher** (en orden de especificidad): `merchant_exact` ("COPEC" →
  Combustible), `description_contains` ("LIDER" → Supermercado), `regex` (casos
  complejos; requiere confirmación extra al crear).
- **Procedencia (`origin`)**: `system_seed` (pack inicial chileno: LIDER, JUMBO,
  UNIMARC → Supermercado; COPEC, SHELL, ARAMCO → Combustible; UBER, DIDI, CABIFY →
  Transporte; STARBUCKS, JUAN VALDEZ → Cafetería; etc. — ~40 reglas editables),
  `user` (creada a mano), `promoted` (nacida de correcciones, §5).
- **Evaluación**: por `priority` descendente, primer match gana. Empate de prioridad →
  gana el patrón más largo (más específico). La decisión registra `rule_id`
  (ADR-008) → siempre se sabe qué regla actuó.
- **Dry-run obligatorio**: antes de activar una regla, el sistema muestra cuántas
  transacciones históricas matchearía y qué reclasificaría. Una regla **jamás**
  reclasifica el pasado sin confirmación explícita, y nunca pisa decisiones `user`.
- **Higiene**: `hits_count` por regla; reglas con 0 hits en 6 meses se listan para poda.
  Conflictos detectados (dos reglas activas que matchean lo mismo con categorías
  distintas) se muestran en la página de salud.

Por qué reglas primero: costo $0, latencia ~0, deterministas, explicables y testeables.
El objetivo explícito del sistema es que la **cobertura costo-cero** (docs/10 §4) crezca
mes a mes: la IA es el mecanismo para descubrir conocimiento, las reglas para consolidarlo.

## 4. Pipeline completo de clasificación (orden estricto)

```
transacción (ya normalizada y deduplicada por ImportService, docs/03 §4-5)
  1. Motor de reglas (§3)                       → hit: decisión decided_by=rule. Fin. $0
  2. Caché de comercio (mismo merchant ya       → hit: decisión decided_by=rule
     clasificado igual ≥2 veces, sin conflicto)   (vía regla implícita). Fin. $0
  3. ¿ai.enabled y presupuesto ok? (docs/11)    → no: a cola de revisión. Fin. $0
  4. LLM batch (hasta 30 transacciones/llamada):
       prompt versionado = taxonomía del usuario
         + K decisiones de usuario más similares (pg_trgm sobre description_norm)
         + transacciones (fecha, monto, moneda, descripción normalizada)
       salida JSON estricto: [{id, category, merchant, confidence}]
       → registro en ai_calls; decisión por transacción con ai_call_id (ADR-008)
  5. Validación dura: categoría inexistente en taxonomía → a revisión (jamás crear
     categorías silenciosamente)
  6. ai.shadow_mode=true → TODO a revisión (la decisión queda registrada como sugerencia)
     confidence ≥ ai.confidence_threshold → auto-asignada (is_current=true)
     confidence < umbral                  → a cola de revisión
  7. Corrección del usuario → nueva decisión decided_by=user que supersede (ADR-008)
     → alimenta §5. Regla dura: una decisión ai/rule jamás supersede a una user.
```

Datos enviados al LLM: **solo** descripción normalizada, monto, moneda, fecha y
taxonomía. Nunca números de cuenta, saldos, banco ni identidad; sanitizador previo con
test (docs/06 §4). Con Ollama local, nada sale del PC.

## 5. Aprendizaje de correcciones (sin base vectorial en MVP — ADR-007)

1. **Promoción a regla:** mismo comercio corregido a la misma categoría 2 veces →
   propuesta de regla `origin=promoted` (confirmación de 1 clic, con dry-run §3). El
   conocimiento queda determinista y gratis.
2. **Few-shot dinámico:** decisiones `user` más similares por `pg_trgm` inyectadas al prompt.
3. **Caché de comercio** (§4.2).

Ruta de evolución con gates medibles (embeddings/pgvector): ADR-007 §5.

## 6. Selección de modelos por tarea

| Tarea | Recomendado | Razón |
|---|---|---|
| Clasificación batch | Modelo pequeño/barato u Ollama local | Alto volumen, tarea simple |
| Bootstrap de plantillas de correo nuevas | Modelo medio | Poco frecuente, precisión importa |
| NL Q&A y recomendaciones (Fase 6) | Modelo grande | Razonamiento sobre agregados |

Los correos en régimen se parsean con plantillas/regex, no con LLM (docs/05 §2): el LLM
ayuda una vez a construir la plantilla, no en cada correo.

## 7. Evaluación (la IA se mide, no se confía)

- Dataset dorado: decisiones validadas por el usuario (crece solo).
- Job semanal `ai_weekly_eval`: accuracy vs correcciones, % a revisión, costo por
  transacción — por (provider, model, prompt_version), consultable por SQL gracias a ADR-008.
- Cambiar modelo/proveedor/prompt exige correr la evaluación en modo comparación
  (`dry_run`: decisiones `task=eval` que no tocan `is_current`) antes de activar.
- Indicadores de aprendizaje definidos en docs/10 §4.

## 8. Calibración inicial (modo sombra)

Semanas 1-2 del MVP: `ai.shadow_mode=true` — la IA sugiere, el usuario decide todo.
Con la matriz real de aciertos se calibra `ai.confidence_threshold` (el 0.85 default es
un placeholder reconocido, no una decisión). Salir de sombra requiere: precisión efectiva
≥90% en la ventana de sombra.

## 9. Revisión crítica

- **Riesgo:** confianzas autorreportadas por LLMs están mal calibradas → por eso el modo
  sombra es obligatorio y el umbral es un flag, no una constante.
- **Riesgo:** las reglas semilla chilenas pueden clasificar mal casos personales (comprar
  en COPEC comida, no bencina) → las reglas del usuario tienen prioridad sobre las seed,
  y toda regla es editable/desactivable.
- **Caso borde:** dos decisiones simultáneas sobre la misma transacción (job batch +
  corrección manual) → `is_current` se actualiza con constraint parcial único
  (`WHERE is_current`) + la corrección user siempre gana.
- **Mejora futura:** clasificador local (TF-IDF + regresión logística) con >3.000
  decisiones etiquetadas podría sacar al LLM del camino crítico.
