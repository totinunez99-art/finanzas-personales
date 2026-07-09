# 11 — Configuración y Feature Flags

> Estado: **Aprobado** · Creado: 2026-07-06 (revisión CTO)

## 1. Análisis previo: el riesgo de esta funcionalidad es ella misma

Los feature flags son deuda técnica con fecha de vencimiento incorporada: cada flag
duplica los caminos de ejecución a probar. Un sistema mono-desarrollador con flags
huérfanos es peor que uno sin flags. Por eso esta estrategia incluye reglas de
eliminación, no solo de creación. Servicios externos (LaunchDarkly, Unleash) quedan
descartados sin ADR: son para equipos con despliegues graduales a miles de usuarios.

## 2. Arquitectura: dos niveles

### Nivel 1 — Configuración estática (`.env` + pydantic-settings)

Para infraestructura y secretos: conexión DB, credenciales IMAP, API keys, puertos,
nivel de log, `AI_PROVIDER` por defecto y cadena de fallback. Cambiar exige reiniciar el
contenedor. Validación al arrancar: config inválida = el proceso no arranca con error claro.

### Nivel 2 — Flags dinámicos (tabla `app_settings`)

Para comportamiento ajustable en runtime desde el dashboard, sin redeploy ni reinicio:

| Flag | Tipo | Default | Efecto |
|---|---|---|---|
| `ai.enabled` | bool | true | OFF: nada llama al LLM; todo lo no resuelto por reglas va a revisión manual. El sistema sigue 100% funcional (docs/04 §1) |
| `ai.provider_override` | str? | null | Fuerza un proveedor sin tocar `.env` (para pruebas A/B) |
| `ai.shadow_mode` | bool | **true** | ON: la IA decide pero NO auto-asigna; toda decisión va a revisión. Arranque del MVP en sombra (docs/04 §8) |
| `ai.auto_classify` | bool | true | OFF: pipeline corre pero solo sugiere |
| `ai.confidence_threshold` | float | 0.85 | Umbral de auto-asignación; se calibra con datos, no en código |
| `ai.monthly_budget_usd` | float | 5.0 | Superado: `ai.enabled` se comporta como false + evento `ai.budget_exceeded` |
| `connectors.email_polling` | bool | true | Apaga el polling IMAP sin apagar el worker |
| `experimental.<nombre>` | bool | false | Funcionalidades en desarrollo, ocultas en UI |

Mecánica:
- Tabla `app_settings`: `key`, `value jsonb`, `updated_at`, `updated_by`. Lectura vía
  `SettingsService` con caché en proceso (TTL 30 s) — ni un query por transacción, ni
  esperar reinicio.
- **Registro tipado en código**: cada flag se declara en un catálogo (`shared/flags.py`)
  con tipo, default, descripción y dueño. Leer un flag no declarado = error en arranque.
  Strings mágicos prohibidos.
- Precedencia: `app_settings` > `.env` > default del catálogo.
- Todo cambio de flag emite `settings.changed` en `domain_events` (quién, qué, cuándo,
  valor anterior → auditable, ADR-009).

## 3. Reglas anti-sprawl (obligatorias)

1. Todo flag `experimental.*` nace con dueño y fecha de revisión (campo en el catálogo).
2. Flag sin cambios en 3 meses: se promueve a config estática o se elimina junto con su
   rama muerta de código. Se revisa en cada actualización de MASTER_PROJECT.
3. Un flag nuevo requiere justificar por qué no basta configuración estática.
4. Los tests cubren ambos estados de los flags de comportamiento críticos (`ai.enabled`,
   `ai.shadow_mode`); flags experimentales se testean solo en su estado default hasta salir de experimental.

## 4. Integración con el resto del diseño

- `ai.shadow_mode` y `ai.confidence_threshold` son los mandos de la calibración inicial (docs/04 §8).
- El presupuesto conecta con `ai_calls` (costo real acumulado, docs/10 §3).
- La página de salud muestra los flags activos con valor no-default (visibilidad de estado del sistema).

## 5. Revisión crítica

- **Riesgo:** caché TTL 30 s implica que un cambio de flag tarda hasta 30 s en aplicar a
  un job en curso. Aceptable; documentado en la UI ("aplica en <1 min").
- **Riesgo:** `app_settings` como jsonb sin esquema fuerte → mitigado por el catálogo
  tipado que valida en lectura y escritura.
- **Caso borde:** flag cambiado a mitad de un batch → el batch lee flags una vez al
  inicio y los fija para toda su ejecución (consistencia intra-batch).
- **Limitación honesta:** con un solo usuario, la mitad del valor de los flags es
  disciplina de desarrollo (poder desactivar lo a medio hacer), no operación. Está bien:
  ese es exactamente el uso que los mantiene pocos.
