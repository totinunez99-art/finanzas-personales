# 07 — Automatización y Operación

> Estado: **Aprobado** · Última actualización: 2026-07-06
> Decisión formal: [ADR-005](adr/ADR-005-scheduler-python-no-n8n.md)

## 1. Análisis: qué se automatiza con qué

| Proceso | Herramienta | Justificación |
|---|---|---|
| Polling IMAP | Worker Python (APScheduler) | Necesita parsers y modelos del core; hacerlo en n8n duplicaría lógica |
| Clasificación batch | Worker Python | Ídem: usa pipeline `ai/` |
| Tipos de cambio diarios | Worker Python | Llamada HTTP trivial; no justifica otra herramienta |
| Backup diario + prueba de restauración | Worker Python + scripts shell | Debe correr junto a la DB |
| Evaluación semanal de IA | Worker Python | Usa el dataset dorado en la DB |
| Detección de suscripciones/recurrencias (Fase 2) | Worker Python (SQL + heurísticas) | Análisis sobre datos, no integración |
| Notificaciones al usuario (futuro) | **Candidato n8n/webhook** | Único caso donde n8n aportaría: integrar Telegram/email de salida sin escribir código |

**Conclusión (ADR-005):** en el MVP, todo proceso repetitivo vive en `workers/jobs/` con
APScheduler. n8n queda pre-aprobado condicionalmente solo para integraciones externas
de *salida*, según los criterios C1-C3 definidos en ADR-005 (≥2 integraciones reales en
backlog, consumo solo vía API, y esfuerzo Python equivalente >2 días u OAuth manual).

**Cron del sistema / eventos / colas:** descartados en MVP. Cron de Windows/WSL es menos
portable que APScheduler dentro del contenedor; eventos y colas (Redis/RabbitMQ) son
infraestructura sin problema que resolver a esta escala. Las fronteras del código
(services llamados por jobs) hacen que migrar a una cola sea un cambio localizado si llega el día.

## 2. Calendario de jobs (MVP)

| Job | Frecuencia | Nota |
|---|---|---|
| `sync_email` | al arrancar + cada 15 min | incremental por UID |
| `fetch_exchange_rates` | al arrancar + diario 09:00 | idempotente; rellena días faltantes hacia atrás |
| `classify_pending` | al arrancar + cada 30 min | respeta presupuesto LLM |
| `daily_backup` | primer arranque del día | ver docs/06 §5 |
| `ai_weekly_eval` | semanal | métricas al dashboard |

Todos los jobs: idempotentes, con lock (no dos instancias del mismo job), registro en
`job_runs` (inicio, fin, resultado, error) visible en la página de salud. Como el PC no
corre 24/7, cada job usa la lógica "al arrancar, ejecuta lo atrasado" (APScheduler
`misfire_grace_time` + catch-up propio donde aplique).

## 3. Entornos y ciclo de desarrollo

- `docker compose up` = producción local. `compose --profile dev` monta código en vivo.
- Migraciones Alembic: se aplican al arrancar `api` (seguro mono-usuario; en Fase 7 se separa).
- GitHub: repo privado. CI (GitHub Actions, gratis): lint (ruff) + tipos (mypy) + tests
  (pytest) en cada push. Sin CD: el deploy es `git pull && docker compose up --build` local.

## 4. Revisión crítica

- **Riesgo:** APScheduler vive dentro del proceso worker; si el worker muere, no hay
  jobs. Mitigación: `restart: unless-stopped` en compose + página de salud que muestra
  último run de cada job.
- **Limitación:** "ejecutar lo atrasado" puede acumular trabajo tras vacaciones (500
  correos). Los jobs procesan en lotes acotados para no saturar el arranque.
- **Caso borde:** cambio de hora (Chile tiene DST) → jobs con hora fija usan timezone
  explícita `America/Santiago`.
