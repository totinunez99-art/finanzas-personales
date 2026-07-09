# 10 — Estrategia de Observabilidad

> Estado: **Aprobado** · Creado: 2026-07-06 (revisión CTO) · Reemplaza y amplía docs/06 §6

## 1. Principio de diseño

A la escala de este sistema (un usuario, un PC no-24/7), la base de datos de dominio
**ES** el almacén de métricas. Casi todo lo que se quiere observar (importaciones,
clasificaciones, costos, correcciones) ya vive en tablas transaccionales; duplicarlo en
un stack de series de tiempo (Prometheus/Grafana) sería una segunda fuente de verdad que
mantener para cero consumidores adicionales. La observabilidad se diseña desde el inicio,
pero con tres capas proporcionales:

1. **Logs estructurados** — diagnóstico técnico (¿qué pasó dentro del proceso?).
2. **Métricas como vistas SQL** sobre tablas de dominio — salud y tendencias (¿cómo va el sistema?).
3. **`domain_events`** (ADR-009) — traza de negocio por entidad (¿qué le pasó a este dato?).

## 2. Capa 1: Logs estructurados

- `structlog` con salida JSON; nivel por módulo vía configuración (docs/11).
- Campos obligatorios en todo log: `timestamp`, `level`, `module`, `correlation_id`
  (mismo id que `domain_events` para cruzar traza técnica con traza de negocio).
- Middleware de FastAPI registra por request: ruta, status, duración ms.
- Prohibido en logs: secretos, descripciones completas de transacciones en nivel INFO, PII.
- Destino: stdout (`docker compose logs`) + archivo con rotación 7 días.

## 3. Capa 2: Métricas — catálogo completo (requisito CTO → fuente → definición)

| Métrica | Fuente (tabla) | Definición exacta |
|---|---|---|
| Importaciones exitosas / fallidas | `import_batches` | conteo por `status`, por período y por cuenta |
| Filas por batch (leídas/insertadas/duplicadas/reconciliadas/fallidas) | `import_batches` | columnas propias del batch |
| Tiempos de respuesta API | logs (middleware) | p50/p95 por ruta, ventana 7 días |
| Latencia LLM | `ai_calls.latency_ms` | p50/p95 por proveedor y modelo |
| Duración de jobs | `job_runs` | fin − inicio, por job |
| Costo acumulado de IA | `ai_calls.cost_estimate` | suma mensual, comparada contra presupuesto (`monthly_ai_budget`, docs/11) |
| Consumo de tokens | `ai_calls.tokens_in/out` | suma por día/mes/proveedor/modelo/prompt_version |
| Clasificaciones automáticas | `classification_decisions` | conteo `decided_by IN (rule, ai)` con `is_current`, por período |
| Correcciones manuales | `classification_decisions` | conteo `decided_by=user` que supersede una decisión `rule/ai` |
| **Aprendizaje de la IA** (3 indicadores, ver §4) | `classification_decisions`, `classification_rules` | definidos abajo |
| Estado de workers | `job_runs` | última ejecución y resultado por job; rojo si job vencido según su frecuencia |
| Estado de backups | `job_runs` + metadato del último backup verificado | verde <24 h; amarillo <48 h; rojo ≥48 h o restauración de prueba fallida |
| Correos sin parsear | `unparsed_emails` | conteo pendiente + tasa parseados/recibidos (alerta de degradación de plantillas, docs/05) |
| Precisión IA vs dataset dorado | `classification_decisions` (task=eval) | job semanal `ai_weekly_eval` (docs/07) |

Implementación: vistas SQL (`metrics_*`) versionadas en migraciones + endpoints
`/health` (liveness simple) y `/metrics/summary` (JSON para el dashboard). Las vistas
son la definición canónica de cada métrica: una métrica sin vista no existe.

## 4. Definición de "porcentaje de aprendizaje de la IA"

El término es ambiguo; se definen tres indicadores medibles y complementarios:

1. **Precisión efectiva (30 días):** `1 − (correcciones a decisiones automáticas / decisiones automáticas del período)`.
   Mide si el sistema se equivoca menos con el tiempo. Es la métrica principal.
2. **Cobertura costo-cero:** % de transacciones del período resueltas por reglas + caché
   de comercio (sin LLM). Mide si el conocimiento se está consolidando en reglas deterministas.
3. **Tasa de promoción:** reglas creadas desde correcciones (`origin=promoted`) por mes.
   Mide que el ciclo corrección→regla funciona.

"Aprender" = (1) sube o se mantiene alta, (2) sube, y el volumen de correcciones por
transacción baja. Las tres se grafican como tendencia mensual en la página de salud.

## 5. Página de salud (dashboard)

Única superficie de consumo en MVP. Secciones: estado de jobs y backups (semáforo),
importaciones recientes con sus contadores, gasto y tokens IA del mes vs presupuesto,
indicadores de aprendizaje (§4), correos sin parsear, últimos errores (de logs), y
timeline de `domain_events` filtrable por entidad.

## 6. Alertas

Un PC apagado no puede alertar: las alertas del MVP son **pasivas** — semáforos en la
página de salud + resumen de anomalías al abrir el dashboard ("backup vencido", "12
correos sin parsear", "presupuesto IA al 80%"). Alertas activas (Telegram) = primer
candidato n8n según criterios de ADR-005; hasta entonces, ninguna promesa de notificación.

## 7. Criterio de evolución

Adoptar OpenTelemetry/Prometheus/Grafana solo si: servidor 24/7, o multiusuario (Fase 7),
o >3 servicios separados. Antes de eso, cualquier stack de monitoreo es más infraestructura
que sistema observado.

## 8. Revisión crítica

- **Riesgo:** vistas SQL sobre tablas transaccionales pueden ponerse lentas con años de
  datos. Mitigación: todas las vistas filtran por ventana temporal; si duele, vistas
  materializadas refrescadas por job (cambio localizado).
- **Limitación:** p50/p95 de API desde logs es artesanal. Suficiente para un usuario;
  OTel lo reemplazaría en Fase 7.
- **Caso borde:** reloj del PC mal configurado rompe ventanas temporales — los timestamps
  se generan en Postgres (`now()`), no en Python, para tener una sola fuente de tiempo.
