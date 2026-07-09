# 13 — Estrategia de Golden Dataset

> Estado: **Aprobado** · Creado: 2026-07-06 (pre-primer parser)
> Regla de oro: **el primer parser nace acompañado de sus casos golden, o no nace.**

> **Decisión del dueño (sesión 11):** el Golden principal se basa en documentos REALES
> anonimizados. Los PDFs sintéticos existen solo como COMPLEMENTO para casos difíciles
> de conseguir (multipágina, rollover diciembre-enero, mes sin movimientos). El
> anonimizador de PDFs re-renderiza el contenido real con sensibles reemplazados
> (mismo motor de render que los sintéticos). Los originales reales sirven además como
> regresión local que la CI nunca ve.

## 1. Principios

1. **Privacidad primero:** los archivos originales (cartolas, correos) contienen la
   identidad financiera completa del usuario. JAMÁS entran a git. Solo lo anonimizado
   y verificado se versiona (docs/06). Esta regla prevalece sobre cualquier comodidad.
2. **Casos inmutables:** un caso golden mergeado no se edita; se agrega uno nuevo.
   La estabilidad de las pruebas depende de que el pasado no cambie bajo los pies.
3. **Todo bug de producción se convierte en caso golden** antes de corregirse
   (ya era convención en docs/08 §4; aquí se formaliza el mecanismo).
4. **La anonimización es determinista:** mismo dato real → mismo dato falso, siempre.
   Sin esto, la reconciliación email↔cartola y el dedup serían imposibles de probar
   (el mismo comercio debe verse igual en ambas fuentes anonimizadas).

## 2. Estructura de `golden/`

```
golden/
├── README.md                    # guía operativa corta (apunta a este doc)
├── originals/                   # ⛔ NUNCA en git (.gitignore). Zona de trabajo local.
│   ├── README.md                #    (única excepción versionada: esta advertencia)
│   ├── statements/<banco>/<cuenta>/<YYYY-MM>.<ext>
│   └── emails/<banco>/<tipo-de-correo>/<YYYY-MM-DD>_<n>.eml
├── cases/                       # ✅ versionado: SOLO anonimizado + esperado
│   ├── _TEMPLATE/               # plantilla de caso (copiar para crear uno nuevo)
│   ├── statements/<banco>/<caso>/     # 1 carpeta = 1 caso autocontenido
│   │   ├── input.csv|xlsx|pdf         # cartola anonimizada
│   │   ├── expected.json              # salida esperada del parser
│   │   └── case.yaml                  # manifiesto (id, origen, qué valida, estado)
│   ├── emails/<banco>/<tipo>/<caso>/  # input.eml + expected.json + case.yaml
│   ├── scenarios/<caso>/              # casos multi-fuente: dedup y reconciliación
│   │   ├── inputs/                    # N archivos (emails + cartola del período)
│   │   ├── expected.json              # estado final esperado tras importar todo
│   │   └── case.yaml
│   ├── classification/<caso>/         # transacciones etiquetadas (dataset dorado exportado)
│   ├── edge/<caso>/                   # casos borde (sintéticos o derivados de reales)
│   └── errors/<caso>/                 # entradas que DEBEN fallar con error específico
└── tools/                       # anonimizador + verificador de fugas (con el 1er parser)
```

Convenciones: nombre de caso `NNN-descripcion-corta` (ej: `001-mes-normal`,
`002-compra-usd-facturada-clp`). El `NNN` es estable y nunca se reutiliza, ni siquiera
tras eliminar un caso.

### Manifiesto `case.yaml` (contrato mínimo)

```yaml
id: statements/bancochile/001-mes-normal
schema_version: 1            # versión del formato expected.json
source: real-anonimizado     # real-anonimizado | sintetico | derivado-de-bug
created: 2026-07-15
validates: [parser]          # parser | dedup | reconciliation | classification | error
status: active               # active | quarantine (excluido de CI, con motivo y fecha)
notes: "Cartola CSV típica, 42 movimientos, sin cuotas"
bug_ref: null                # issue/commit si nació de un bug
```

### `expected.json` por tipo de caso

- **Parser (statements/emails):** lista canónica de `RawTransaction` (mismos campos del
  contrato en `connectors/base.py`, montos como string decimal) + resumen esperado del
  batch (`rows_read`, `rows_failed`, y cuadratura de saldos si la cartola la trae).
- **Scenario (dedup/reconciliación):** estado final esperado tras importar todos los
  inputs en orden: conteo por `status` (confirmed/reconciled/orphan/provisional),
  pares reconciliados (por source_ref), duplicados rechazados.
- **Classification:** pares (descripción normalizada, categoría esperada) validados por
  el usuario. Es el **dataset dorado de evaluación de IA** (docs/04 §7) exportado de la
  DB — la DB sigue siendo la fuente; el export versionado congela conjuntos de
  evaluación comparables entre modelos.
- **Error:** tipo de excepción esperada y fragmento del mensaje. Un parser que "arregla"
  silenciosamente una entrada corrupta es un bug, no una mejora.

## 3. Anonimización

### Qué se reemplaza (obligatorio) y qué se preserva (obligatorio)

| Se reemplaza (determinista) | Se preserva intacto |
|---|---|
| RUT, nombres de personas | **Montos** (la cuadratura y el dedup dependen de ellos) |
| Números de cuenta/tarjeta (last4 consistente) | **Fechas** (reconciliación usa ventanas ±3 días) |
| Emails y teléfonos personales | **Estructura del archivo** byte-a-byte fuera de los campos sensibles |
| Nº de operación/folio (mapeo 1→1) | Nombres de comercios (son datos públicos y la clasificación los NECESITA) |
| Direcciones | Códigos de sucursal/glosas genéricas del banco |

Decisión explícita: los nombres de comercios NO se anonimizan — sin ellos, los casos de
clasificación y el motor de reglas serían de utilería. Lo que revelan ("Tomás compró en
LIDER") solo es sensible junto a la identidad, que sí se elimina.

### Mecanismo

- `golden/tools/anonymize.py` (se implementa junto al primer parser): reemplazo
  determinista con mapeo persistente **local** (`originals/mapping.json`, gitignored) —
  mismo RUT real → mismo RUT falso en cartolas Y correos, para que los escenarios de
  reconciliación sigan siendo coherentes entre fuentes.
- `golden/tools/verify_no_leaks.py`: escáner que corre en CI sobre `golden/cases/`:
  patrones de RUT, PAN (Luhn), emails, y una lista local de términos prohibidos
  (nombres reales, gitignored). **CI falla si detecta una fuga.** Cuatro ojos: además,
  toda adición a `cases/` se revisa a mano antes del commit.
- PDF: la anonimización editando PDF es frágil; para cartolas PDF el original se
  transcribe a un PDF regenerado o se reduce al texto extraído + un PDF sintético
  equivalente. Se documentará por banco al conocer los formatos reales (no verificado aún).

## 4. Cómo se usa el golden dataset para validar cada capa

| Capa | Mecánica de validación |
|---|---|
| **Parsers** | Test parametrizado por cada caso de `cases/statements/` y `cases/emails/`: parsear `input.*` → comparar contra `expected.json` campo a campo. Los casos de `errors/` afirman que el parser FALLA con el error declarado (tolerancia cero a ambigüedad, docs/05 §3). |
| **Deduplicación** | `scenarios/`: importar los mismos inputs dos veces → segunda pasada debe producir 0 inserciones; casos con compras idénticas mismo día validan `intra_day_seq`. |
| **Reconciliación** | `scenarios/` con correos + cartola del período: el estado final (reconciled/orphan/provisional) debe coincidir con `expected.json`, incluyendo los casos ambiguos que DEBEN ir a revisión en vez de auto-reconciliar. |
| **Clasificación** | `cases/classification/` como conjunto de evaluación congelado: el job `ai_weekly_eval` y toda comparación de modelo/prompt (ADR-008) corren contra el mismo conjunto → resultados comparables. Cambiar de modelo exige pasar esta evaluación primero (docs/04 §7). |
| **Migraciones futuras** | Test de replay: DB vacía → migrar a head → importar TODOS los escenarios golden → verificar conteos/estados. Una migración que rompe la importación de datos históricos falla aquí, no en producción. |
| **Regresiones** | Todo bug real → caso `derivado-de-bug` con `bug_ref` ANTES del fix. El conjunto crece de forma monótona; la CI corre siempre el 100% de los casos `active`. |

Ejecución: los tests golden viven en `tests/golden/` marcados `@golden` (subconjunto de
integración: requieren PG real). CI los corre en el job de integración.

## 5. Proceso de actualización sin perder estabilidad

1. **Agregar caso (camino normal):** copiar `_TEMPLATE/` → anonimizar → escribir
   `expected.json` **a mano o verificado a mano** (nunca aceptar ciegamente la salida
   del parser como esperado: eso convierte el test en tautología) → `verify_no_leaks`
   → PR con revisión visual.
2. **Caso inmutable:** si el comportamiento esperado cambia legítimamente (ej: se decide
   normalizar distinto), NO se edita el caso: se hace **bump de `schema_version`** con
   una migración de expected explícita en el mismo PR que cambia el comportamiento, y el
   diff de cada expected se revisa caso a caso. La historia de git es el registro de por
   qué cambió cada esperado.
3. **Caso roto/flaky:** pasa a `status: quarantine` con motivo y fecha en `case.yaml`
   (la CI lo excluye pero lo reporta). Cuarentena >30 días → se arregla o se elimina en
   revisión explícita. Prohibido borrar casos para poner la CI verde.
4. **Un banco cambia de formato (R-02):** el formato viejo NO se elimina — se agrega el
   nuevo como casos nuevos. Los históricos siguen validando que cartolas antiguas
   reimportadas (restore de backup, replay) sigan funcionando.
5. **Revisión periódica:** al cierre de cada fase se audita cobertura: cada banco con
   ≥1 mes normal, ≥1 caso de cada tipo de correo, ≥1 caso de error, y los bordes del
   catálogo (§6) cubiertos o justificados como pendientes en este doc.

## 6. Catálogo inicial de casos borde a cubrir (checklist para la Fase 2)

Compras duplicadas legítimas el mismo día · compra USD facturada en CLP (docs/05 §6) ·
cartola con cuadratura que no cierra · cuotas ("03/12") en glosa · reversa/anulación de
cargo · transferencia entre cuentas propias · correo de compra sin cartola posterior
(huérfano real) · cartola re-descargada con glosas levemente distintas (R-02) · archivo
vacío o de otro banco (debe fallar) · encoding roto (Latin-1 vs UTF-8) · montos con
separador de miles chileno ("1.234.567") · mes con 0 movimientos.

## 7. Revisión crítica

- **Riesgo:** escribir `expected.json` a mano es tedioso → tentación de generarlo con el
  parser y aceptarlo. Mitigación parcial: la regla §5.1 + revisión de PR; honestidad: con
  un solo desarrollador, esta regla depende de disciplina personal. Es el punto más débil.
- **Riesgo:** el mapeo de anonimización local (`mapping.json`) se pierde → casos nuevos
  dejarían de ser coherentes con los viejos. Mitigación: el mapeo entra al backup cifrado
  (docs/06 §5), nunca a git.
- **Limitación:** originals/ vive solo en este PC; otro colaborador no puede regenerar
  casos. Aceptado: es un proyecto personal; si llega Fase 7, se rediseña con datos sintéticos.
- **No verificado:** formatos reales de cartola/correo. La sección §3 (PDF) y §6 se
  ajustarán con las primeras muestras reales — este doc se revisa al cerrar Fase 2.
