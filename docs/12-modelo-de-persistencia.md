# 12 — Modelo de Persistencia: inventario, justificación y autoevaluación

> Estado: **Aprobado** · Creado: 2026-07-06 (revisión pre-Fase 2)
> Fuente de verdad del esquema: `src/finanzas/core/models/` + `migrations/versions/0001`.
> Este documento describe y justifica; NO modifica el esquema.

## 1. Inventario completo (13 tablas + 1 de tooling)

### users
- **Responsabilidad:** identidad del dueño de los datos.
- **Almacena:** email, nombre. Sin credenciales (sin login en local, docs/06 §1).
- **Módulos:** todos (raíz del scoping por `user_id`, ADR-002).
- **Relaciones:** padre de accounts, categories, transactions, rules, decisions, import_batches, unparsed_emails.
- **Justificación:** el seguro barato contra el retrofit multiusuario: agregarla después tocaría cada tabla y cada query.
- **Si se elimina:** todo el modelo pierde su raíz; migrar a SaaS (Fase 7) exigiría reescribir el esquema completo. Es la tabla más barata de mantener y la más cara de retrofitear.

### accounts
- **Responsabilidad:** contenedor de movimientos: cuenta corriente, TC, línea, ahorro, efectivo.
- **Almacena:** banco, tipo, moneda, last4, saldo inicial + fecha (el saldo actual se DERIVA, nunca se almacena mutable).
- **Módulos:** core (Import/Reconciliation/Reporting), connectors (resolución de `account_hint`).
- **Relaciones:** users→accounts→transactions; referenciada por import_batches.
- **Justificación:** el dedup y la reconciliación son POR CUENTA; sin esta tabla ambos serían ambiguos.
- **Si se elimina:** imposible distinguir la misma compra vista desde TC y desde cuenta corriente; el constraint `uq(account_id, dedup_hash)` desaparece y con él la idempotencia.

### categories
- **Responsabilidad:** taxonomía de clasificación (jerarquía máx. 2 niveles), editable por el usuario.
- **Almacena:** nombre, padre, kind (expense/income/transfer), flags system/active.
- **Módulos:** core, ai (validación dura de salida del LLM, docs/04 §4.5).
- **Relaciones:** transactions, rules y decisions apuntan aquí; self-FK para jerarquía.
- **Justificación:** la taxonomía como datos (no como enum en código) permite que el usuario la moldee sin deploys, y que el LLM se valide contra ella.
- **Si se elimina:** clasificación imposible; categorías hardcodeadas romperían el aprendizaje y la corrección.

### transactions — corazón del dominio
- **Responsabilidad:** cada movimiento financiero, con su ciclo de vida (provisional→reconciled / confirmed / orphan) y su estado ACTUAL de clasificación (denormalizado deliberado, ADR-008).
- **Almacena:** montos Numeric(18,4), moneda original, descripción cruda inmutable + normalizada, dedup_hash, referencias de origen, cuotas crudas (jsonb, deuda D-02).
- **Módulos:** core (todos los services), api, futuro dashboard financiero.
- **Relaciones:** accounts, categories, import_batches, self-FK `reconciled_with_id`, decisions.
- **Justificación:** es el sistema. Todo lo demás existe para poblar, explicar o agregar esta tabla.
- **Si se elimina:** no hay proyecto.

### import_batches
- **Responsabilidad:** auditoría y control de cada importación de archivo.
- **Almacena:** sha256 del archivo (unicidad por cuenta), período, contadores leídas/insertadas/duplicadas/reconciliadas/fallidas, estado, error.
- **Módulos:** core (ImportService), connectors, dashboard (métricas docs/10 §3).
- **Relaciones:** users, accounts; transactions referencia su batch de origen.
- **Justificación:** idempotencia de archivo (reimportar = no-op) + las métricas de importación exigidas por la revisión CTO salen íntegramente de aquí.
- **Si se elimina:** reimportaciones duplicadas silenciosas a nivel de archivo, cero trazabilidad de "de dónde salió esta transacción", métricas de importación imposibles.

### classification_rules
- **Responsabilidad:** motor determinista, primera línea del pipeline (docs/04 §3).
- **Almacena:** matcher (tipo+patrón), categoría destino, prioridad, procedencia (seed/user/promoted), hits.
- **Módulos:** ai (pipeline), core, dashboard (gestión de reglas).
- **Relaciones:** users, categories; FK circular con decisions (una regla puede nacer de una corrección).
- **Justificación:** conocimiento consolidado a costo $0; el objetivo medible del sistema es que la cobertura de reglas crezca (docs/10 §4).
- **Si se elimina:** toda clasificación pasaría por LLM: más costo, no-determinismo, y el "aprendizaje" perdería su destino final.

### classification_decisions
- **Responsabilidad:** historial auditable de TODA decisión de clasificación (ADR-008). Una corrección manual es una decisión más que supersede.
- **Almacena:** quién decidió (rule/ai/user), con qué regla o llamada LLM, confianza, cadena de supersesión, flag `is_current` (unique parcial).
- **Módulos:** ai (few-shot desde decisiones user, evaluación), core, dashboard (¿por qué esta categoría?).
- **Relaciones:** transactions, users, categories, rules, ai_calls, self-FK superseded_by.
- **Justificación:** auditoría, comparación entre modelos y reprocesamiento exigidos por revisión CTO; reemplazó a la tabla de feedback para no duplicar responsabilidad.
- **Si se elimina:** solo quedaría el estado final en transactions: sin historial, sin dataset dorado, sin métricas de aprendizaje, sin replay. La IA volvería a ser un oráculo no auditable.

### ai_calls
- **Responsabilidad:** registro de cada llamada a un LLM (ADR-008).
- **Almacena:** proveedor, modelo y versión reportada, prompt (id+versión+sha), tokens, costo, latencia, respuesta cruda.
- **Módulos:** ai (único escritor), dashboard (costo/presupuesto, docs/10 §3).
- **Relaciones:** decisions→ai_calls (N decisiones por llamada batch).
- **Justificación:** control de presupuesto y comparación entre modelos con SQL simple; separada de decisions porque una llamada cubre ~30 transacciones (granularidad distinta).
- **Si se elimina:** costo IA invisible (violación directa de un requisito CTO), imposible atribuir decisiones a modelo/prompt.

### exchange_rates
- **Responsabilidad:** valores diarios UF/USD en CLP.
- **Almacena:** fecha, moneda, tasa, fuente. Unique(fecha, moneda).
- **Módulos:** workers (job diario), core (Reporting convierte al vuelo, docs/03 §6).
- **Relaciones:** ninguna FK — se cruza por (fecha, moneda) de cada transacción.
- **Justificación:** el histórico es barato de acumular e imposible de reconstruir con garantías si la fuente gratuita desaparece (R-08).
- **Si se elimina:** reportes multi-moneda imposibles; las transacciones UF/USD quedarían sin valorización CLP histórica correcta.

### domain_events
- **Responsabilidad:** event log unificado append-only (ADR-009); absorbe al antiguo audit_log.
- **Almacena:** tipo (catálogo cerrado), entidad, actor, correlation_id, payload de referencias.
- **Módulos:** core (`emit()` en la misma transacción que cada mutación), dashboard (timeline).
- **Relaciones:** referencias débiles (entity+entity_id) a propósito: un evento sobrevive a cambios del esquema referenciado.
- **Justificación:** timeline por transacción ("¿qué le pasó a este dato?"), auditoría CTO; regla dura: NO es load-bearing, las métricas salen de tablas de dominio.
- **Si se elimina:** depurar la reconciliación se vuelve arqueología de logs; se pierde la traza de negocio, no el estado (por diseño).

### job_runs
- **Responsabilidad:** estado operacional de cada ejecución de job del worker.
- **Almacena:** job, inicio/fin, estado (running/ok/error), detalle jsonb.
- **Módulos:** workers (runner), api/dashboard (semáforo de salud, docs/10 §3).
- **Relaciones:** ninguna FK (operacional puro).
- **Justificación:** "estado de workers" y "estado de backups" del requisito CTO se responden con un GROUP BY sobre esta tabla.
- **Si se elimina:** el worker sería una caja negra; un job muerto pasaría inadvertido durante semanas en un PC no-24/7.

### app_settings
- **Responsabilidad:** flags dinámicos de comportamiento (docs/11 nivel 2).
- **Almacena:** clave→valor jsonb envuelto `{"v": ...}`; quién y cuándo actualizó.
- **Módulos:** shared define el contrato (flags.py); core (SettingsService) lee/escribe; todos consumen.
- **Relaciones:** ninguna; cada cambio emite `settings.changed` en domain_events.
- **Justificación:** apagar la IA, salir de modo sombra o ajustar el umbral sin redeploy — requisito CTO explícito.
- **Si se elimina:** todo cambio de comportamiento exigiría editar .env y reiniciar; la calibración del umbral (docs/04 §8) sería tortuosa.

### unparsed_emails
- **Responsabilidad:** cola de correos bancarios que ningún parser reconoció.
- **Almacena:** referencia IMAP, asunto, remitente, razón de fallo, estado de resolución.
- **Módulos:** connectors (escritor), dashboard (cola visible + métrica de degradación de plantillas).
- **Relaciones:** users.
- **Justificación:** la mitigación principal de R-02 (bancos cambian plantillas): un formato nuevo es información, jamás se descarta en silencio (docs/05 §2).
- **Si se elimina:** la degradación de parsers sería invisible hasta que la cartola mensual revele el hueco — semanas de datos provisionales perdidos en silencio.

### alembic_version (tooling)
Una fila con la revisión aplicada. La gestiona Alembic; se lista por completitud.

## 2. Clasificación por tipo

| Tipo | Tablas |
|---|---|
| **Dominio financiero** | accounts, categories, transactions, import_batches, exchange_rates |
| **Infraestructura/operación** | job_runs, unparsed_emails, alembic_version |
| **Auditoría** | domain_events, classification_decisions (doble rol: dominio de clasificación + auditoría) |
| **IA** | ai_calls, classification_rules (motor determinista de la capa de clasificación), classification_decisions |
| **Configuración** | app_settings |
| **Transversal** | users (raíz de scoping, ADR-002) |

Nota honesta: `classification_decisions` y `classification_rules` resisten una sola
etiqueta — son dominio de clasificación, insumo de IA y auditoría a la vez. Forzar una
categoría única sería taxonomía por deporte.

## 3. Autoevaluación del modelo

### 3.1 ¿Sobre-normalización?

**No.** 13 tablas para este alcance es un modelo contenido; señales concretas:
- No hay tablas puente innecesarias ni entidades separadas "por pureza" (ej: merchant NO
  es tabla propia — es un string en transactions/decisions; normalizarlo hoy sería
  sobre-diseño clásico. Se reevalúa si Fase 2+ necesita metadatos por comercio).
- Hay denormalización deliberada y documentada donde importa el rendimiento de lectura:
  el estado actual de clasificación vive copiado en `transactions` (ADR-008), con un
  único escritor y actualización en la misma transacción DB.

### 3.2 ¿Duplicidad?

Tres solapamientos, todos deliberados; se documentan para que nadie los "arregle" por error:

1. **transactions.classified_by/confidence/category_id ↔ classification_decisions.**
   No es duplicidad accidental: es caché de lectura vs historial. Riesgo real: divergencia
   por un escritor indisciplinado. Protección: regla de único escritor (docs/08 §2) —
   cuando exista el service, un test de convención debe verificarla.
2. **job_runs(status=error) ↔ domain_events(job.failed).** Un fallo de job se registra
   dos veces. Justificación: job_runs es estado operacional consultable (semáforo);
   el evento es traza de negocio correlacionable. Costo: una fila extra por fallo. Aceptado.
3. **transactions.merchant ↔ classification_decisions.merchant.** La decisión guarda el
   merchant PROPUESTO en ese momento; la transacción, el vigente. Es snapshot histórico,
   no copia redundante.

### 3.3 ¿Tablas prematuras? — el hallazgo principal de esta revisión

Cuatro tablas existen ANTES que el código que las alimenta. Veredicto por tabla:

| Tabla | ¿Prematura? | Veredicto |
|---|---|---|
| `ai_calls`, `classification_decisions` | Sí — la IA es Fase 2+ | **Defendible pero anticipada.** Se crearon ahora porque el esquema de auditoría define el contrato del pipeline (ADR-008) y migrar transactions después es más caro. Costo de mantener vacías: ~0. Riesgo real: cuando se implemente el pipeline, el esquema puede necesitar ajustes → habrá migración 000X de todos modos. Se aceptó pagar ese riesgo a cambio de que Fase 1 dejara el contrato completo. |
| `unparsed_emails` | Sí — no hay conector IMAP | Igual razonamiento; tabla trivial (0 FK salientes salvo users). Costo ~0. |
| `exchange_rates` | Parcial — no hay job aún | La MENOS prematura: el job de tasas es el candidato a primer job real precisamente porque el histórico no se puede reconstruir después (R-08). |

Conclusión: prematuridad consciente y barata, no accidental. Regla hacia adelante: **ninguna
tabla nueva sin el código que la alimente en el mismo PR** — el crédito de "esquema
anticipado" se agotó con la Fase 1.

### 3.4 Oportunidades de simplificación

- **app_settings con wrapper `{"v": ...}`:** leve fealdad a cambio de escalares sin
  ambigüedad en JSONB. Alternativa (columna por tipo) sería más tablas/columnas para 7
  flags. Mantener.
- **installment_info jsonb:** es la simplificación (deuda D-02 con fecha de pago en Fase 2);
  la alternativa "tabla installment_plans hoy" sería una tabla prematura más.
- **users en mono-usuario:** la simplificación de eliminarla costaría exactamente el
  rediseño que ADR-002 evita. No simplificar.
- **¿Fusionar job_runs en domain_events?** Tentador (una tabla menos) pero incorrecto:
  mezclaría estado mutable (running→ok) con un log append-only; consultas de semáforo
  se ensuciarían. No fusionar.
- **Simplificación real disponible si Fase 2 lo confirma:** si el caché de comercio
  (docs/04 §4.2) se implementa como reglas implícitas `merchant_exact`, no necesita
  tabla nueva — usar classification_rules con origin propio. Anotado para el diseño de Fase 2.

### 3.5 Veredicto global

El modelo es proporcional al problema: 5 tablas de dominio, el resto es el precio
explícito de tres requisitos no negociables (auditoría CTO, observabilidad sin stack
externo, y multiusuario-sin-retrofit). No hay tabla cuya eliminación no rompa un
requisito documentado. El punto más débil no es el esquema sino su estado: **nada de
esto ha ejecutado contra datos reales** — la revisión que importa ocurrirá cuando el
primer parser real intente llenar `transactions` y la reconciliación se enfrente a
cartolas de verdad. Este documento debe revisarse al cierre de Fase 2.
