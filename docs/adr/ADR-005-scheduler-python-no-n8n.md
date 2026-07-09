# ADR-005 — Automatización: Python para procesos internos; n8n como candidato acotado para integraciones externas de salida

Fecha original: 2026-07-06 · **Revisado: 2026-07-06 (revisión CTO)** · Estado: **Aceptado**
Cambio vs versión anterior: se reemplaza el binario "n8n sí/no" por una frontera de
responsabilidades explícita y criterios medibles de adopción.

## Contexto

El stack preferido del dueño incluye n8n. La revisión CTO exige distinguir dos
responsabilidades que la versión anterior de este ADR trataba como una sola:

- **A. Automatización interna:** scheduler, polling IMAP, clasificación, reconciliación,
  backups, mantenimiento, evaluación de IA.
- **B. Integración externa de salida:** notificaciones y sincronizaciones hacia
  Telegram, WhatsApp, Slack, Notion, Google Drive/Sheets, email saliente, etc.

## Análisis por responsabilidad

### A. Automatización interna → Python + APScheduler (no negociable)

Todos estos procesos necesitan el dominio: modelos, parsers, servicios, transacciones DB.
Orquestarlos desde n8n obligaría a exponer cada paso como endpoint y el flujo n8n sería
solo "llamar endpoints en orden" — una capa de indirection sin lógica propia, con estado
del flujo fuera de git y fuera de pytest. Además:

| Criterio | Worker Python | n8n orquestando |
|---|---|---|
| Acceso al dominio | Directo, tipado | Solo vía API; cada job exige endpoint |
| Testeabilidad | pytest, CI | Export JSON; sin tests unitarios reales |
| Versionado | Git nativo, diff legible | JSON exportado, diff ilegible, deriva fácil |
| Transaccionalidad | Misma transacción DB | Imposible entre pasos HTTP |
| Piezas de infraestructura | 0 nuevas | +1 contenedor, +1 almacén propio, +RAM (~400 MB) |
| Secretos | Un almacén (.env) | Duplicados en n8n |

### B. Integración externa de salida → aquí n8n SÍ tiene un caso

Comparación honesta para el caso "enviar reporte semanal a Telegram y guardar Excel en Drive":

**n8n — ventajas:** cientos de conectores mantenidos por terceros; OAuth de Google
gestionado por la herramienta (el flujo de tokens/refresh de Google API a mano es
trabajo real y tedioso); reintentos y manejo de errores visuales; modificar un flujo de
notificación sin tocar código ni redesplegar; webhooks entrantes triviales.

**n8n — desventajas:** contenedor + base de datos propia que respaldar; flujos viven
fuera del repo (mitigable exportando JSON a git, con fricción); segundo lugar donde
viven credenciales; en un PC no-24/7 pierde parte de su gracia (webhooks entrantes no
alcanzables); curva de aprendizaje y mantenimiento de otra herramienta.

**Python puro — ventajas:** una sola base de código, testeable, tipada, secretos
centralizados. **Desventajas:** cada integración se escribe y mantiene a mano; OAuth de
Google a pulso; el costo crece linealmente con cada servicio nuevo.

## Decisión

1. **Responsabilidad A: siempre Python + APScheduler.** Sin excepciones mientras el
   proceso necesite el dominio. Esto incluye el polling IMAP: aunque Gmail es "externo",
   el valor está en el parsing con fixtures y tests, que exige Python.
2. **Responsabilidad B: n8n queda pre-aprobado condicionalmente.** Se incorpora cuando
   se cumplan LAS TRES condiciones:
   - C1: existen ≥2 integraciones de salida hacia servicios de terceros en el backlog real (no hipotético);
   - C2: dichas integraciones consumen solo la API pública del sistema (nunca la DB);
   - C3: la implementación Python equivalente se estima en >2 días de trabajo o exige
     mantener OAuth flows a mano (Google Drive/Sheets es el caso típico).
3. Reglas si se incorpora: n8n consume solo la API con un token propio; sus flujos se
   exportan a `automation/n8n/` en git en cada cambio; su base se incluye en el backup.
4. El MVP no cumple C1 (cero integraciones de salida en alcance) → el MVP se construye sin n8n.

## Consecuencias

- (+) La frontera queda definida antes de que exista el problema; incorporar n8n después no es un rediseño.
- (+) MVP con una pieza menos de infraestructura.
- (−) Si el dueño quiere aprender n8n como objetivo personal, esta decisión lo pospone;
  ese objetivo es legítimo pero distinto y debe declararse explícitamente.
- Primer candidato real esperado: notificaciones Telegram de la página de salud (ver docs/10 §6).
