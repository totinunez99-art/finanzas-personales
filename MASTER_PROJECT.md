# MASTER_PROJECT — Finanzas Personales

> **Memoria viva del proyecto.** Se actualiza en cada sesión de trabajo. Si algo
> importante se decidió en un chat y no está aquí o en un ADR, no existe.
> Última actualización: **2026-07-08 (sesión 12 — regla de Quality Gates; Gate 1 en validación)**

## 1. Estado actual

**Fase: 2 — Sprint 1 (Import Wizard) implementado; PENDIENTE de primera ejecución real.**

Sesión 6 (Sprint 1 completo, bloques B1-B5):
- **B1 Núcleo:** contrato `StatementParser` (sniff/parse) + registry con detección por
  confianza; `ImportService` (preview sin escritura + import con dedup por
  `dedup_hash`+`intra_day_seq`, eventos, contadores); migración **0002**
  (`unrecognized_files`: formato desconocido NO falla, se registra).
- **B2 Conector `generic_csv_v1`:** formato puente documentado (docs/14 §4), reglas
  deterministas de montos chilenos; **6 casos golden** (normal, duplicados mismo día,
  bordes de montos/fechas, formato desconocido, fecha ilegible) + runner golden +
  `verify_no_leaks` (escáner RUT/PAN/email en CI, con test de autodetección).
- **B3 API:** `/accounts` (GET/POST), `/imports/preview`, `/imports` (confirm, 409 si
  repetido), `/imports` (GET), `/transactions` (GET con total). `get_current_user` por
  dependencia (ADR-002). Test de integración del ciclo completo con dedup.
- **B4 Dashboard:** páginas **Importar** (drag&drop → detección → métricas
  nuevos/duplicados → confirmar/cancelar) y **Movimientos** (contador, listado con
  tipo cargo/abono, importaciones recientes). Solo vía API.
- **B5:** docs/14-import-wizard.md + este documento.

⚠ Sigue vigente: **nada de esto ha ejecutado aún** (sin entorno de ejecución en las
sesiones). Validación = CI en primer push + primer `docker compose up`.

Sesión 7 (preparación del cierre del sprint — SIN funcionalidades nuevas):
- Estabilidad: exception handlers globales (AppError → status+mensaje, nunca 500
  críptico), UUIDs inválidos → 422.
- **Demo Mode**: `scripts/demo.py` idempotente + 3 CSVs ficticios (julio incluye un
  duplicado deliberado de junio para demostrar dedup entre archivos; agosto queda para
  la prueba manual del wizard). Bootstrap compartido en `core/services/bootstrap.py`
  (seed y demo sin lógica duplicada).
- **docs/15**: instalación en minutos + tabla de troubleshooting (incluye el riesgo
  OneDrive+Docker en Windows: ejecutar desde ruta no sincronizada).
- **docs/16**: checklist de validación en 4 fases (A infra, B demo, C datos reales,
  D cierre) con resultados numéricos esperados exactos y registro de hallazgos.
- El sprint queda **EN VALIDACIÓN**: lo cierra Tomás completando docs/16, no el código.

Sesión 8 — primer error de ejecución real y rediseño del bootstrap:
- **Causa raíz:** worker dependía de api con `service_started`, que se cumple al arrancar
  el contenedor, no al terminar las migraciones que corrían DENTRO del comando de api →
  heartbeat contra DB vacía (`relation "job_runs" does not exist`). Deuda D-05 mal pagada.
- **2º bug encontrado en la revisión:** `scripts/` no se copiaba a la imagen Docker
  (seed/demo por `exec` habrían fallado).
- **Solución estructural:** servicio **`bootstrap`** one-shot (espera PG con reintentos →
  `alembic upgrade head` → usuario por defecto), api/worker con
  `service_completed_successfully`; demo como profile opt-in (`docker compose run --rm demo`);
  seed automático (criterio: un solo comando). Defensa en profundidad: `wait_for_db` +
  `assert_migrated` en worker, seed y demo — ningún proceso asume tablas.
- D-05 (migraciones al arrancar la api) queda **pagada**: las migraciones ya no viven en
  el comando de la api.
- docs/15/16 y README actualizados; hallazgo registrado en docs/16 §5 fila 1.
- Riesgos remanentes del arranque: ver docs/15 §5 (cambio de POSTGRES_DB con volumen
  existente; OneDrive+Docker). El fix del compose (anchors YAML, profiles) se valida en
  la siguiente ejecución real de Tomás.

Sesión 9 — **Sprint 2, Parte A implementada** (valor de uso; sin IA/OCR/reglas):
- `core/services/reporting.py`: filtros (búsqueda insensible a tildes, fechas, monto
  por magnitud, cargo/abono) + `stats_summary` por moneda con última importación.
  Tests de integración con casos numéricos exactos.
- API: `GET /transactions` con filtros; `GET /stats/summary?period=YYYY-MM`.
- Dashboard: home = dashboard financiero (métricas del período, última importación,
  botón importar, tabla con filtros); Movimientos = vista completa + historial de
  importaciones; salud → página **Administración**. Componentes compartidos (sin duplicar tabla).
- docs/17 con decisiones: métricas por moneda sin sumar entre monedas; filtro de monto
  ciego a moneda (documentado y testeado); "este mes" = mes calendario.
- **Parte B BLOQUEADA:** conector Banco **Edwards (PDF)** espera cartolas reales en
  `golden/originals/statements/edwards/` (instrucciones enviadas a Tomás). Al llegar:
  anonimizar → casos golden → parser + pdfplumber (dep justificada en docs/17 §4).

Sesión 10 (2026-07-08) — **análisis del formato Edwards con cartola real** (docs/18):
- Primera cartola real recibida (junio, 1 página) y analizada con pdfplumber/pypdf en sandbox.
- Hallazgos clave: PDF **cifrado con contraseña** (el wizard necesitará campo de clave;
  no se persiste); texto nativo de alta calidad (sin OCR); generador COLDview con
  **metadata estructurada CVQT_*** (cuenta, período, saldos, totales por categoría) que
  habilita cuadratura contra dos fuentes; columnas cargo/abono/saldo solo distinguibles
  por posición X (extract_table de pdfplumber inservible aquí); fechas DD/MM sin año
  (rollover diciembre-enero); saldo solo en la última fila de cada día; cuadratura
  global verificada exacta en la muestra.
- Diseño completo del parser en docs/18 (13 puntos + estrategia). SIN código aún.
- **Bloqueado por:** (a) ratificación del diseño por Tomás; (b) más muestras (≥2 meses,
  ideal multipágina y mes sin movimientos); (c) decisión UX de contraseña (recomendado: pedir cada vez).

Sesión 11 — diseño ratificado con ajustes (ImportResult, ValidationReport tipado,
ParserCapabilities, confianza determinista, golden principal = reales anonimizados;
sintéticos solo complemento). **Bloque 1 IMPLEMENTADO:**
- Contrato: `ImportResult` reemplaza a ParsedStatement; `ValidationCheck/Report` tipados;
  `ParserCapabilities`; `password` opcional en sniff/parse; `confidence_from_signals`.
- `pdf_utils` en connectors (is_encrypted_pdf/password_opens; core lo usa vía frontera permitida).
- ImportService: tercer estado del preview `password_required` (mensaje de no
  persistencia), `_assert_validation` (defensa: validación roja jamás importa),
  persistencia de trazabilidad; **migración 0003** (parser_version, detected_format,
  validation jsonb, opening/closing_balance, extraction_confidence en import_batches).
- API: `password` Form opcional en preview/import; batch expone trazabilidad.
  UI: campo de contraseña bajo demanda + panel de chequeos de validación con confianza.
- Deps nuevas: pypdf + pycryptodome. generic_csv v1.1.0 adaptado.
- **HITO: primera ejecución real de tests — 39/39 unit+golden PASARON en sandbox**
  (Python 3.10 + shim StrEnum; la CI en 3.12 sigue siendo autoritativa). py_compile
  de todo el árbol limpio (única excepción esperable: sintaxis 3.12 de repositories).
- Siguiente: bloque 2 (anonimizador PDF + caso golden real junio + generador sintético
  complementario) → bloque 3 (parser edwards_cc_pdf contra esos casos + regresión local).

Sesión 12 — **regla nueva: Quality Gates (docs/19)**. Ningún bloque sobre base no
validada. Hallazgos de la sesión: la carpeta OneDrive NO soporta git (locks del
filesystem verificados — quedó un `.git` roto que Tomás debe borrar a mano); el repo
git vivirá en el clon de ejecución `C:\Finanzas personales\Finanzas personales`.
**Gate activo: G1+G2 (infraestructura + importación CSV), EN VALIDACIÓN** — lo cierra
Tomás con: sincronizar árboles → git init/push → CI verde → compose limpio → docs/16
fases A-B-C. El bloque 2 de Edwards NO comienza hasta cerrar ese gate. docs/19 §Gate
activo tiene el checklist; los comandos exactos fueron entregados en el chat de sesión 12.

⚠ **El código fue escrito sin entorno de ejecución disponible en la sesión.** Está
auto-revisado pero NO ejecutado. La validación real ocurre en: (1) primer push a GitHub
(CI corre lint, tipos, fronteras, tests unitarios y migraciones contra PG real), y
(2) primer `docker compose up` local. Hasta entonces, asumir que habrá ajustes menores.

- Sesión 1 (2026-07-06): decisiones de contexto (Chile CLP+UF+USD, PC local con Docker,
  ingesta dual email+cartola, alcance MVP). Docs 01–09 + ADR-001..007.
- Sesión 2 (2026-07-06): **revisión de arquitectura del CTO completada.** Resultado:
  - ADR-005 reescrito: frontera interna/externa; n8n pre-aprobado condicionalmente para
    integraciones de salida (criterios C1-C3), Python para todo lo interno.
  - ADR-007 reescrito: comparación ChromaDB/pgvector/Qdrant + gates objetivos de adopción.
  - **ADR-008 nuevo:** auditoría/versionado de decisiones IA → tablas `ai_calls` +
    `classification_decisions` (reemplazan `ai_usage` y `classification_feedback`),
    prompts versionados en git.
  - **ADR-009 nuevo:** event log unificado `domain_events` desde el MVP (absorbe `audit_log`).
  - **docs/10 nuevo:** estrategia de observabilidad (métricas = vistas SQL sobre dominio).
  - **docs/11 nuevo:** configuración en dos niveles + feature flags con reglas anti-sprawl.
  - docs/04 profundizado: motor de reglas completo (semillas chilenas, dry-run,
    conflictos, procedencia) + pipeline actualizado + modo sombra formalizado.
  - Esquema propagado a docs/02, 03, 06, 08.

## 2. Decisiones de arquitectura (índice de ADRs)

| ADR | Decisión |
|---|---|
| [ADR-001](docs/adr/ADR-001-monolito-modular.md) | Monolito modular, no microservicios |
| [ADR-002](docs/adr/ADR-002-multiusuario-diferido.md) | `user_id` desde día 1; multiusuario diferido a Fase 7 |
| [ADR-003](docs/adr/ADR-003-ingesta-dual.md) | Email = señal provisoria; cartola = fuente de verdad; scraping descartado |
| [ADR-004](docs/adr/ADR-004-abstraccion-llm.md) | Capa LLM propia multi-proveedor; sin framework |
| [ADR-005](docs/adr/ADR-005-scheduler-python-no-n8n.md) | Interno: Python+APScheduler. Externo de salida: n8n condicional (C1-C3). *Rev. CTO* |
| [ADR-006](docs/adr/ADR-006-streamlit-tras-api.md) | Streamlit solo-API para MVP; UI descartable por diseño |
| [ADR-007](docs/adr/ADR-007-chromadb-diferido.md) | Vectorial diferida con gates; ruta pgvector primero. *Rev. CTO* |
| [ADR-008](docs/adr/ADR-008-auditoria-decisiones-ia.md) | Decisiones IA auditables: `ai_calls` + `classification_decisions` + prompts versionados |
| [ADR-009](docs/adr/ADR-009-event-log-unificado.md) | `domain_events` append-only desde MVP; sin event sourcing |

## 3. Implementado (sesión 3 — Fase 1, pendiente de validación en ejecución)

- **Estructura del repo** según docs/02 §6: `src/finanzas/{shared,core,connectors,ai,api,workers,dashboard}`.
- **pyproject.toml**: deps, ruff, mypy (estricto en core/shared), import-linter (capas + prohibición dashboard→core), pytest.
- **Docker Compose**: db (PG16, solo localhost), api (migra al arrancar + uvicorn), worker, dashboard. Un solo Dockerfile.
- **shared/**: config pydantic-settings, logging structlog JSON con correlation_id, catálogo tipado de flags (docs/11), errores.
- **Modelos SQLAlchemy** (13 tablas, esquema docs/03 completo incl. ADR-008/009).
- **Migración 0001** escrita a mano (+pg_trgm, índice GIN trigram, unique parcial de decisión vigente, FK circular rules↔decisions).
- **Servicios base**: `emit()` de eventos, SettingsService (caché TTL, escritura auditada), health/metrics, dedup hash + normalización.
- **API**: `/health`, `/metrics/summary`, middleware de timing + correlation_id.
- **Worker**: APScheduler con run_job() (job_runs, evento job.failed, catch-up) + heartbeat.
- **Dashboard Streamlit mínimo**: conectividad, estado de jobs, flags no-default (solo vía API).
- **Tests**: unitarios (flags, dedup, config, catálogo de eventos) + integración (migración aplica, anti-deriva modelos↔migración vía autogenerate, round-trip con rebote de duplicado en DB).
- **CI**: lint+format+mypy+import-linter+tests unitarios; job de integración con PG16 real.
- **scripts/seed.py**: usuario por defecto idempotente.

NO implementado (deliberado): parsers, IMAP, IA, clasificación, dashboards financieros, backups job.

Sesión 4: **docs/12-modelo-de-persistencia.md** creado (revisión pre-Fase 2). Inventario
completo de las 13 tablas con justificación y autoevaluación. Hallazgos: sin
sobre-normalización; 3 solapamientos deliberados documentados (§3.2); 4 tablas
conscientemente prematuras (ai_calls, classification_decisions, unparsed_emails,
exchange_rates) — aceptadas con la regla nueva: **ninguna tabla futura sin el código que
la alimente en el mismo PR**. Simplificación anotada para Fase 2: el caché de comercio
puede ser reglas implícitas en classification_rules, sin tabla nueva.

Sesión 5: **docs/13-golden-dataset.md** + esqueleto `golden/` (README, originals/
gitignored, cases/_TEMPLATE). Reglas clave: originales JAMÁS en git; anonimización
determinista con mapeo local (montos y fechas intactos, comercios intactos, identidad
reemplazada); casos inmutables (comportamiento nuevo = caso nuevo, cambios legítimos =
bump de schema_version con diff revisado); todo bug → caso golden antes del fix;
verificador de fugas en CI. `golden/cases/` reemplaza al plan anterior de
`tests/fixtures/` para datos bancarios (los tests golden vivirán en `tests/golden/`,
marker propio dentro de integración). Los tools (anonymize.py, verify_no_leaks.py) se
implementan junto al primer parser — regla de docs/12 §3.3: código y su infraestructura
en el mismo PR.

## 4. Pendiente — próximos pasos priorizados

| # | Tarea | Bloqueada por |
|---|---|---|
| 1 | **Dueño:** push a GitHub → CI verde; `docker compose up --build` → seed → importar un CSV de referencia → criterio de éxito del sprint | — |
| 2 | Corregir hallazgos de la primera ejecución (esperable: ajustes menores) | 1 |
| 3 | **Dueño:** descargar cartolas Banco de Chile (las tiene en su correo) → `golden/originals/statements/bancochile/` (mínimo 2 meses, CSV/XLSX si existe la opción, PDF como último recurso) | — |
| 4 | `golden/tools/anonymize.py` + casos golden bancochile → **conector `bancochile`** (checklist docs/14 §5) | 2, 3 |
| 5 | Semilla de categorías + reglas chilenas (con pantalla que las use) | 2 |
| 6 | Conector IMAP + plantillas de correo Banco de Chile + reconciliación email↔cartola | 4 |
| 7 | Capa `ai/` + motor de reglas + pipeline de clasificación (modo sombra) | 4, 5 |
| 8 | Dashboard: cola de revisión de clasificaciones | 7 |
| 9 | Jobs reales del worker + backup diario + vistas `metrics_*` | 4, 6 |
| 10 | Calibrar `ai.confidence_threshold` tras 2 semanas de sombra (salida: precisión ≥90%) | 7, 8 |

## 5. Problemas conocidos

Ninguno (sin código). Riesgos de diseño en [docs/09](docs/09-riesgos-y-deuda-tecnica.md).

## 6. Riesgos abiertos (top 3 — registro completo en docs/09)

1. **R-01 Abandono por fricción** — riesgo existencial; el MVP entero se diseñó contra él.
2. **R-02 Bancos cambian formatos** — permanente; cola de no-parseados + fixtures + cartola como red.
3. **R-03 Pérdida de datos** — backups probados (docs/06 §5); prerequisito: BitLocker activo.

Nuevo riesgo aceptado en sesión 2: flag sprawl y eventos sin disciplina de emisión —
mitigados con reglas anti-sprawl (docs/11 §3) y test de convención (ADR-009).

## 7. Preguntas abiertas para el dueño

1. ¿Qué bancos concretos? (define parsers y su orden)
2. ¿Proveedor LLM por defecto y presupuesto mensual? (propuesta: modelo barato, tope US$5/mes)
3. ¿BitLocker activo en el PC? (prerequisito, docs/06)
4. ¿Passphrase de backups a un gestor de contraseñas? (docs/06 §5)
5. ¿n8n es también objetivo de aprendizaje personal? (cambiaría el criterio de ADR-005 §Consecuencias)

## 8. Roadmap resumido

Fases 1–7 en [docs/01 §3](docs/01-vision-y-roadmap.md). Regla anti-scope-creep vigente.
Criterio de salida del MVP: **4 semanas consecutivas de uso diario real con datos confiables.**

## 9. Convención de mantenimiento de este documento

- Toda sesión que cambie código o decisiones actualiza este archivo en el mismo commit.
- Secciones 3, 4, 5 y 6 rotan; la 2 solo crece. Decisiones nuevas → ADR + fila en §2.
- Revisión trimestral de flags (docs/11 §3) se registra aquí.
