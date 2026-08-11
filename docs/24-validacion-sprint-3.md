# 24 — Validación Sprint 3 con datos reales (cartola Edwards)

> Estado: **EN CURSO** · Creado: 2026-07-17 · Rol: Lead QA / Auditor Técnico
> Regla de la fase: **cero funcionalidades nuevas, cero refactors** salvo bug crítico.
> Primero diagnóstico con evidencia; las soluciones se discuten después.

## 0. Correcciones de expectativa (antes de medir)

Declaradas ANTES de ver los resultados para que no parezcan excusas después:

1. **"Decisiones por IA" será 0.** El AiResolver es un stub por diseño (Sprint 3 excluyó
   IA explícitamente). No es un hallazgo: es el plan. Igual se reporta la columna.
2. **"Decisiones manuales" será 0 al inicio.** Solo existen tras usar el teach de
   comercios o corregir categorías. Se reporta su evolución durante la validación.
3. **"% correctas" exige ground truth que solo tiene el dueño.** El sistema puede medir
   *cobertura* (% resuelto) solo; *corrección* requiere que Tomás revise movimiento a
   movimiento. El protocolo incluye esa tabla de revisión (§3). Sin esa revisión, los %
   de corrección quedarán como "no calculable aún" — no se inventan.
4. **Deltas, semanas y anomalías dirán "sin base/insuficiente"** con un solo mes de
   datos (docs/23 §5). Verificar que lo digan honestamente ES parte de la validación.
5. **Flow es derivado:** su corrección es idéntica a la corrección de las categorías
   transfer (ADR-010 §6). Se mide la detección de internos, no la derivación.

## 1. Preflight (gates previos, lado dueño)

| Paso | Acción | Resultado |
|---|---|---|
| P1 | robocopy OneDrive → repo ejecución | ✅ 2026-07-17 |
| P2 | git add/commit/push | ✅ commit: f259544 |
| P3 | GitHub Actions verde (2 jobs) | ✅ CI #3, 1m 19s (verificado por Chrome) |
| P4 | `docker compose up --build` (bootstrap aplica migración 0005) | ✅ 9/9, bootstrap Exited OK (nota: primer intento falló por Docker Desktop apagado; el motor auto-restauró contenedores viejos y hubo que reconstruir) |
| P5 | Salud OK: `/health` → `{"status":"ok","db":true,"migration":"0005"}` | ✅ verificado por Chrome |

## 1.1 Hallazgos pre-importación

- **V-01 (Media):** `/resolution/resolvers` reporta `flow` como stub. Causa:
  `implemented = {"merchant", "category"}` hardcodeado en `resolution.py:32` (Bloque 3),
  no actualizado en Bloque 4. Solo afecta al endpoint informativo; la ejecución usa
  `REGISTRY` y sí incluye flow (`default_order` correcto). Fix propuesto (NO aplicado):
  derivar `implemented` del registro (p. ej. atributo en la clase o detectar
  `skipped_reason="no implementado aún"`), eliminando el set manual.

- **V-02 (CRÍTICA, corregida con aprobación del dueño):** imposible confirmar la
  importación de un PDF cifrado desde la UI. Causa raíz: la contraseña vivía en el
  session_state DEL WIDGET (`key="import_pdf_password"`); Streamlit elimina el estado de
  un widget cuando deja de renderizarse — y el campo desaparece justo cuando la clave
  funciona. Al pulsar Confirmar (rerun completo), la clave ya no existía → preview exigía
  clave de nuevo → `st.stop()` antes del botón → loop infinito. Ningún test lo cubría:
  la UI tiene cero cobertura (los golden prueban parser/API; el checklist wizard de
  docs/16 B4-B7 estaba pendiente y los demo CSV no llevan clave). Fix: clave en entrada
  de sesión propia (`pdf_password`) + guard anti-loop para clave incorrecta. La clave
  sigue viviendo solo en memoria de sesión y en los requests. Detectado en el primer
  intento real de importación — evidencia del valor de validar con datos reales.

## 1.2 Limpieza de datos demo (aprobada por el dueño, 2026-07-17)

- Auditoría previa (`scripts/audit_demo_data.sql`): 3 batches demo, 31 tx, 34 eventos,
  0 decisiones; riesgos FK/contaminación todos en 0. Hallazgos: el pipeline nunca había
  corrido en esta base (0 categorías/reglas — semillas pendientes) y solo existía la
  cuenta demo.
- Borrado (`scripts/cleanup_demo_data.sql`, transacción única): DELETE 0/34/31/3 +
  cuenta demo (con guardas NOT EXISTS). ~180 ms. Verificaciones V1–V4 en 0;
  V5 final: 0/0/0/0/0 cuentas y 1 usuario.
- Estado post-limpieza: instalación nueva. `/health` ok migración 0005, `/accounts` vacío.
  La primera importación real será el PRIMER dato del sistema.

## 1.3 Cambio aprobado durante validación: siembra del catálogo en bootstrap

Decisión del dueño (2026-07-17): el catálogo (categorías/reglas) no debe depender de la
primera ejecución del pipeline. Cambio: `scripts/bootstrap.py` llama a `ensure_seed(user)`
tras crear el usuario por defecto. Se CONSERVA la llamada defensiva en
`CategoryStage.prepare` (misma función idempotente, dos puntos de entrada; los tests de
integración dependen de ella y protege usuarios futuros creados fuera del bootstrap).
Se eligió bootstrap sobre "creación de primera cuenta" para no acoplar la inicialización
del catálogo a un evento de dominio sin relación causal.
Impacto: instalación nueva queda con catálogo completo antes de la primera importación.
Riesgo: si la siembra falla, el bootstrap bloquea el arranque (fail-fast deliberado).

## 2. Protocolo de importación y pipeline

1. Importar la cartola real (Importar → PDF → contraseña → confirmar). Registrar:
   leídas / insertadas / duplicadas / descartadas / errores / warnings / confianza de
   extracción / cuadratura.
2. **Simular pipeline (dry-run) ANTES de ejecutar** y guardar el reporte: es la
   predicción auditable de lo que hará.
3. Ejecutar pipeline real. Comparar contra la simulación: deben coincidir (si difieren,
   bug crítico → detener validación).
4. Fuentes de auditoría: `GET /transactions`, `GET /stats/summary`, `GET /stats/insights`,
   `GET /stats/analytics`, `GET /metrics/summary`, reporte de `/resolution/run`,
   `domain_events` (correlation del batch).

## 3. Métricas — definición exacta (fórmula y fuente)

| Métrica | Fórmula | Fuente | ¿Calculable sin revisión del dueño? |
|---|---|---|---|
| Cobertura comercios | tx con merchant asignado / tx totales | transactions.merchant_source | Sí |
| Cobertura categorías | tx con category_id / tx totales | transactions.category_id | Sí |
| % sin clasificar | 1 − cobertura categorías | ídem | Sí |
| % internos / operacionales | tx flow=internal / total (y complemento) | transactions.flow | Sí |
| % comercios CORRECTOS | correctos según dueño / asignados | tabla de revisión §3.1 | **No — requiere revisión** |
| % categorías CORRECTAS | correctas según dueño / asignadas | tabla de revisión §3.1 | **No — requiere revisión** |
| % internos bien detectados | internos confirmados / internos reales según dueño | tabla de revisión §3.1 | **No — requiere revisión** |
| Decisiones por origen | conteo por decided_by / merchant_source | classification_decisions, transactions | Sí |

### 3.1 Tabla de revisión (ground truth)

Se genera con TODOS los movimientos del período: fecha, descripción, monto, comercio
asignado (y origen), categoría asignada (y regla), flow. Tomás marca ✔/✘ por columna y
anota el valor correcto donde falle. De ahí salen los % de corrección y la lista de
reglas/comercios a enseñar (§6 del encargo).

## 4. Resultados — importación real (2026-07-19)

Se importaron DOS cartolas reales de cuenta corriente Edwards (enero y febrero 2026),
no la de junio prevista. Ambas confirmadas, sin intervención manual posterior.

| Batch | Período | Leídas | Insertadas | Duplicadas | Fallidas | Confianza | Validación |
|---|---|---|---|---|---|---|---|
| CartolaCuentaCorriente ENERO.pdf | 2025-12-30 → 2026-01-30 | 58 | 58 | 0 | 0 | 1.000 | 6/6 OK |
| CartolaCuentaCorriente FEBRERO.pdf | 2026-01-30 → 2026-02-27 | 56 | 56 | 0 | 0 | 1.000 | 6/6 OK |

- Cuadratura global, abonos/cargos vs metadata CVQT, saldo final, encadenado diario y
  páginas completas: **12/12 chequeos exactos** al peso. Cero warnings, cero errores.
- 114 transacciones, 116 domain_events (114 `transaction.imported` + 2 `batch.completed`).
- **Pipeline NO ejecutado**: 0 decisiones, 0 categorías asignadas, 0 flow. Estado esperado
  (la ejecución es manual por diseño; requiere aprobación del dueño).
- Sin solapamiento entre batches pese a que los períodos comparten el 30-01 (0 duplicados).

**Veredicto del conector (G3):** el parser Edwards funciona sobre datos reales de un
formato que NO estaba en el golden (cuenta corriente con línea de crédito, 2 páginas,
114 movimientos) con cuadratura exacta contra la metadata del banco. Es el resultado más
sólido de la validación.

## 5. Hallazgos e inconsistencias

Numeración continúa la de §1.1. Ninguno corregido: diagnóstico primero.

### CRÍTICOS

- **V-03 — La cartola de cuenta corriente rompe el supuesto central de la etapa flow.**
  El catálogo semilla asume una tarjeta de crédito: solo `CARGO POR PAGO TC` marca
  interno. Los datos reales muestran ~35 movimientos internos de otra naturaleza:
  `TRANSFERENCIA DESDE LINEA DE CREDI` (13 abonos), `PAGO LINEA DE CRED` (7 cargos,
  $1.923.216), `AMORTIZACION A LINEA DE CREDITO` (6, $377.886), `PAGO TARJETA DE CREDITO`
  ($60.335), `PAGO AUTOMATICO TARJETA DE CREDITO` ($317.599), `GIRO CAJERO AUTOMATICO` (2).
  Predicción: se detectará **1 de ~35** internos (≈3%). Consecuencia financiera medible en
  febrero: de $9.234.964 de "ingreso", $1.127.214 son giros de la línea de crédito (deuda,
  no ingreso); de $7.078.692 de "gasto", ~$2.191.039 son pagos de deuda/tarjeta.
  **La hipótesis de ADR-010 §6 (≥95% de detección de internos) queda REFUTADA fuera del
  caso tarjeta.** Un movimiento de línea de crédito no es gasto ni ingreso: es
  financiamiento, y el modelo actual no tiene ese concepto.
- **V-04 — Regla `INTERES` clasifica un cargo como categoría de ingreso.**
  `INTERESES LINEA DE CREDITO` (2 cargos, $23.990) cae en "Intereses" (kind=income) por la
  regla semilla `description_contains: INTERES`. Un interés pagado se contabilizaría como
  ingreso por categoría. Defecto de la semilla, no del motor: la regla no distingue signo.

### ALTOS

- **V-05 — Personas naturales se registran como "comercios".** El parser extrae
  `merchant_hint` de los prefijos `TRASPASO A:/DE:`, por lo que ~63 transferencias
  personales quedan con merchant = nombre de persona. "Top comercios" mostrará personas,
  y la base de conocimiento de comercios se contamina con nombres propios (además de ser
  dato personal de terceros).
- **V-06 — Transferencias a cuentas propias indistinguibles.** `TRASPASO A:Christian
  Nunez` ($900.000 y $1.500.000) y `TRASPASO DE:Jens Christian Nunez` ($900.000, $60.000)
  aparentan movimientos entre cuentas propias/familiares. Es exactamente el caso ambiguo
  documentado en ADR-010 §7: sin reconciliación multi-cuenta no es resoluble
  automáticamente. Requiere decisión del dueño (ground truth).

### MEDIOS

- **V-07 — La cuenta se creó con tipo `credit_card` siendo cuenta corriente**
  ("FInanzas Tomás Núñez", BancoChile, credit_card). No afecta el cálculo hoy, pero
  contamina la semántica futura (reconciliación tarjeta↔cuenta corriente).
- **V-08 — Pérdida de caracteres no-ASCII en descripciones.** `TRASPASO DE:Javiera
  Jes?s Urrutia` (debería ser "Jesús"). Afecta visualización y coincidencia por texto.
- **V-01** (§1.1) — `/resolution/resolvers` reporta `flow` como stub.

### BAJOS

- **V-09 — Tres cargos idénticos el mismo día** (`PAGO:FLOW *E-CERTCHI`, $18.314,
  2026-01-02). NO es un bug: la cuadratura exacta prueba que el banco los lista así, y el
  `intra_day_seq` los preservó correctamente en vez de colapsarlos. Evidencia positiva del
  diseño de dedup; se registra para confirmación del dueño.
- **V-10 — KPIs actuales sin sentido financiero** hasta resolver V-03: "tasa de ahorro
  23,3%" en febrero mezcla venta de vehículo ($6.200.000 de AUTOMOTRIZ) con giros de línea
  de crédito. Los deltas vs enero (+207,8% gasto) son aritméticamente correctos pero
  financieramente vacíos.

## 5.1 Métricas — estado

Calculables hoy (post-importación, pre-pipeline): cobertura de comercio 0%, de categoría
0%, flow asignado 0%, todo pendiente de resolución. Es el estado esperado.
**No calculables aún:** % de comercios/categorías/flow CORRECTOS — requieren (a) ejecutar
el pipeline y (b) el ground truth del dueño sobre la tabla de revisión (§3.1). No se
inventan estimaciones.

## 6. Experimento dry-run — informe cuantitativo (2026-07-27)

Ejecutado con `POST /resolution/run {dry_run:true}` + `scripts/diagnose_pipeline.py`
(read-only, SAVEPOINT revertido). **Cero escrituras**: verificado por rollback y por
`domain_events` estable en 116.

### 6.1 Cobertura por etapa

| Etapa | Aplicados | Omitidos | Cobertura |
|---|---|---|---|
| merchant | 75 | 39 | 65,8% |
| category | 71 | 43 | 62,3% |
| flow | 114 | 0 | 100% (asignación, no acierto) |

### 6.2 Distribución final (114 movimientos)

| Naturaleza | n | Monto neto |
|---|---|---|
| income | 37 | +$9.441.731 |
| expense | 33 | −$5.827.255 |
| transfer (interno) | 1 | −$640.258 |
| SIN CLASIFICAR | 43 | −$817.946 |

Control de integridad: la suma da $2.156.272 = neto real de ambos períodos. La
aritmética es correcta; la **semántica** es la que falla.

### 6.3 Reglas: 7 de 33 dispararon (21% de utilización)

| Regla | Usos | Veredicto |
|---|---|---|
| `TRASPASO DE:` | 35 | Correcta por regla, vacía por significado |
| `TRASPASO A:` | 28 | Ídem |
| `INTERES` | 2 | **INCORRECTA** (cargo → categoría de ingreso) |
| `SEGURO PROTECCION` | 2 | Correcta |
| `UNIMARC` | 2 | Correcta |
| `CARGO POR PAGO TC` | 1 | Correcta (único interno detectado) |
| `COPEC` | 1 | Correcta |

**63 de 71 clasificaciones (88,7%) caen en dos reglas de transferencia.** El catálogo
semilla —diseñado para retail chileno sobre tarjeta de crédito— es casi inaplicable a una
cuenta corriente: 26 reglas nunca se activaron.

### 6.4 Detección de movimientos internos: **1 de 33 (3,0%)**

| Familia | Movimientos | Monto | Detectados |
|---|---|---|---|
| Línea de crédito (giros, amortización, pago, interés, impuesto) | 30 | $4.094.512 | 0 |
| Pagos de tarjeta (3 denominaciones distintas) | 3 | $1.018.192 | 1 |
| Giro de cajero (efectivo) | 2 | $55.000 | 0 (discutible) |

**Predicción previa: "1 de ~35, ≈3%". Resultado: 1 de 33, 3,0%. Hipótesis confirmada, y
la de ADR-010 §6 (≥95%) definitivamente refutada para cuenta corriente.**

### 6.5 Precisión estimada por etapa

- **Merchant — ≈16% útil.** De 75 asignaciones, ~63 son nombres de personas extraídos de
  `TRASPASO A:/DE:`. Son *contrapartes*, no comercios. (Limitación del diagnóstico: no
  logró leer el patrón de regla usado; se reporta como incógnita, no se estima a ojo.)
- **Category — 97% laxa / 8,5% estricta.** 69/71 coincidieron con lo que la regla
  prometía (fallan las 2 de `INTERES`); pero solo 6/71 aportan significado financiero
  real (Seguros 2, Supermercado 2, Combustible 1, Pago de Tarjeta 1).
- **Flow — 71,9% de acierto, 3,0% de recall en internos.** Precisión del rótulo
  "internal": 100% (1/1, sin falsos positivos). El error es sistemáticamente de
  *omisión*: 32 movimientos internos rotulados como operacionales.

### 6.6 Falsos positivos / falsos negativos

- **Falsos positivos: prácticamente ninguno.** Nada se marcó interno sin serlo; ninguna
  regla clasificó algo que no coincidiera con su patrón. El sistema es conservador, como
  se diseñó.
- **Falsos negativos: 32 internos** (los de 6.4) + 13 giros de línea contados como
  ingreso + `DEP.CHEQ.OTROS BANCOS` ($300.000) sin naturaleza determinada.
- **Falso positivo semántico (categoría ≠ realidad):** `INTERESES LINEA DE CREDITO`
  ($23.990 de costo financiero) contabilizado en una categoría de ingreso.

### 6.7 Impacto financiero medido

Los KPIs de febrero ($9.234.964 ingreso / $7.078.692 gasto / ahorro 23,3%) incluyen
$1.768.886 de giros de línea como "ingreso" y ~$2.325.626 de pagos de deuda como "gasto".
**Ni el ingreso ni el gasto ni la tasa de ahorro son financieramente válidos hoy.**

### 6.8 Casos ambiguos que requieren decisión del dueño

11 transferencias ≥ $200.000 que el sistema no puede resolver solo, en tres clases:
(a) posibles cuentas propias/familiares — `Christian Nunez` (−$900.000, −$1.500.000) y
`Jens Christian Nunez` (+$900.000); (b) probable ingreso real de gran monto —
`AUTOMOTRIZ SU AUTO` (+$6.200.000); (c) contrapartes empresa — `Capitaria Latam`,
`Taurus SpA`, `CARRERA Y ASOCIADOS`, `Cristobal Merino`.

### 6.8.1 Ground truth entregado por el dueño (2026-07-27)

| Contraparte | Realidad declarada | Consecuencia para el modelo |
|---|---|---|
| Christian / Jens Christian Nuñez | Padre. Préstamos recibidos y devueltos | NO es gasto ni ingreso: es **deuda con un tercero** (préstamo → pasivo; devolución → amortización). Cuarto concepto ausente, hermano de M1 |
| AUTOMOTRIZ SU AUTO ($6.200.000) | Venta de su vehículo | NO es ingreso corriente: es **realización de un activo** (cambio de patrimonio de forma, no aumento de riqueza). Distorsiona cualquier promedio de ingresos |
| Cristobal Merino ($2.000.000) | Socio de un negocio en formación | Movimiento **de negocio**, no de consumo personal. Requiere separar ámbito personal/negocio |

Los tres casos confirman M1 desde ángulos distintos: el modelo solo sabe de gasto e
ingreso, y la realidad del dueño incluye deuda (banco y personas), venta de activos y
actividad de negocio mezcladas en la misma cuenta.

## 6.9 Recomendaciones, separadas por naturaleza

**1. BUGS (defectos claros, arreglo acotado)**
- B1 · `INTERES` → categoría de ingreso para un cargo (V-04). **CORREGIDO** por ADR-011:
  la categoría "Intereses" pasó a `finance_cost`.
- B2 · `/resolution/resolvers` declara `flow` como stub (V-01). **CORREGIDO**: la lista
  se deriva del registro (`is_stub`), ya no puede quedar desactualizada.
- B3 · Pérdida de caracteres no-ASCII en descripciones (V-08).
- B4 · Cuenta creada como `credit_card` siendo cuenta corriente (V-07, dato, no código).

**2. REGLAS INSUFICIENTES (el motor funciona; falta catálogo)**
- R1 · Denominaciones de pago de tarjeta no cubiertas: `PAGO TARJETA DE CREDITO`,
  `PAGO AUTOMATICO TARJETA DE CREDITO` ($377.934 mal contabilizados).
- R2 · Familia línea de crédito completa sin reglas (30 movimientos, $4.094.512).
- R3 · `GIRO CAJERO AUTOMATICO`, `DEP.CHEQ.OTROS BANCOS`, `IMPUESTO LINEA DE CREDITO`.
- R4 · Comercios reales sin resolver: `FLOW *E-CERTCHI` (×3), `PRONTO`, `PANADERIA`,
  `MERCADOPAGO*CAMPI/PRODU`, `CRUCERO LAGO`.

**3. PROBLEMAS DEL MODELO CONCEPTUAL (no se arreglan con reglas)**
- M1 · **Falta el concepto de financiamiento/deuda.** Un giro de línea de crédito aumenta
  el efectivo Y la deuda; una amortización reduce ambos. No es ingreso, no es gasto, y
  tampoco es "traspaso entre cuentas propias". El modelo binario
  `operational | internal` no tiene dónde ponerlo. **Este es el hallazgo central de la
  validación.**
- M2 · **`flow` binario es insuficiente.** Se requiere al menos una tercera naturaleza
  (financiamiento) y probablemente distinguir efectivo (giro de cajero = cambio de
  soporte, no consumo).
- M3 · **Comercio ≠ contraparte.** Extraer personas naturales como "comercio" contamina
  la base de conocimiento, distorsiona "top comercios" y guarda datos personales de
  terceros sin necesidad.
- M4 · **"Transferencia" no es una categoría útil.** El 88,7% de las clasificaciones dice
  únicamente "se movió plata con alguien", que es justo lo que el copiloto debería
  explicar. Una transferencia necesita contraparte + propósito, no una etiqueta.
- M5 · **Sin reconciliación multi-cuenta**, los traspasos a cuentas propias son
  indistinguibles de los pagos a terceros (ADR-010 §7, ahora con evidencia real).

**Conclusión del experimento:** el motor (pipeline, dry-run, auditoría, dedup, parser)
funcionó exactamente como se diseñó; lo que falló es el **modelo financiero**, que
representa una tarjeta de crédito, no una cuenta corriente chilena con línea de crédito.
Escribir más reglas sobre este modelo produciría precisión aparente sobre una
representación equivocada. **Recomendación: diseñar la capa conceptual (M1–M2) antes de
tocar el catálogo.**

## 6.10 Medición posterior a ADR-011 (2026-08-10)

Mismo experimento dry-run, ahora con 144 movimientos (tercera cartola importada) y el
modelo de naturaleza. Comparación contra la medición previa:

| Métrica | Antes (114 tx) | Después (144 tx) | |
|---|---|---|---|
| Cobertura de categoría | 62,3% | **91,0%** (131/144) | proyección era ~90% |
| Reglas distintas que dispararon | 7 | **16** | |
| Concentración en las 2 reglas de traspaso | 88,7% | **59,5%** | mejora, M4 sigue vigente |
| Movimientos de línea de crédito clasificados | 0 de 30 | **30 de 30** (26 `debt` + 4 `finance_cost`) | |
| Pagos de tarjeta detectados | 1 de 3 | **8 de 8** | |
| Movimientos fuera de KPIs | 1 · $640.258 | **34 · $6.067.014** | |
| Sin clasificar | 43 | **13** | |

Distribución final: `expense` 48 · `income` 45 · `debt` 26 · `internal` 8 ·
`finance_cost` 4 · sin clasificar 13.

### 6.10.1 Tras cargar las reglas de contraparte del dueño (`scripts/reglas_contrapartes.sql`)

Tres reglas `origin=user`, prioridad 10, **solo en la base de datos** (nunca en código:
son datos personales de terceros). Verificado por dry-run, sin persistir:

| | Antes de las reglas | Después |
|---|---|---|
| Ingreso reportado | $10.831.871 | **$3.641.871** |
| Gasto reportado | $6.164.442 | **$3.764.442** |
| Movimientos fuera de KPIs | 34 · $6.067.014 | **41 · $15.657.014** |
| Naturalezas presentes | 5 | **7** (aparecen `lending` 6 y `asset` 1) |

Las reglas dispararon exactamente donde debían: `CHRISTIAN NUNEZ` ×6 → Préstamos
Personales (`lending`, neto −$1.410.000: el dueño es acreedor neto), `AUTOMOTRIZ SU AUTO`
×1 → Compra y Venta de Bienes (`asset`, $6.200.000 fuera del ingreso).

**Lectura financiera:** con los tres meses reales, ingreso operacional $3.641.871 contra
gasto operacional $3.788.966 (incl. costo financiero). El dueño gastó levemente más de lo
que ingresó — conclusión imposible de ver con el modelo anterior, que mostraba $10,8
millones de "ingreso" y una tasa de ahorro ficticia.

**Lo que la medición NO resolvió (honestidad obligada):**

1. **Los cuatro casos del ground truth siguen mal clasificados** porque dependen de
   contrapartes personales que deliberadamente no se sembraron en código: los préstamos
   del padre ($900.000 + $1.500.000 + $900.000) siguen como Transferencias
   (`income`/`expense`) en vez de `lending`, y la venta del vehículo ($6.200.000) sigue
   como `income` en vez de `asset`. Hasta enseñarlos, el ingreso reportado sigue inflado.
2. **No existe UI para enseñar categorías** — el *teach* actual solo cubre comercios.
   Hoy la única vía es insertar reglas en `classification_rules` por SQL. Deuda nueva
   (Alta) para la Fase 2.
3. **`DEP.CHEQ.OTROS BANCOS`** (3 movimientos, $450.000) queda sin clasificar por decisión
   deliberada: puede ser ingreso o traspaso propio y no hay evidencia para decidirlo.
4. Los 9 comercios sin resolver son de bajo monto y se resuelven enseñando desde la UI.

## 6.11 Auditoría con 8 cartolas (dic-2025 → jul-2026, 280 movimientos)

### ¿Por qué cambian los valores? — cada peso está explicado

Febrero pasó de "ingreso $9.234.964 / gasto $7.078.692" a **$947.750 / $2.487.653**.
La diferencia NO es un error: es la reclasificación, y cuadra al peso.

```
Ingreso: 9.234.964 − 6.200.000 (venta auto) − 900.000 − 60.000 (padre)
                  − 1.127.214 (giros línea de crédito)            = 947.750  ✓
Gasto:   7.078.692 − 2.400.000 (préstamos al padre)
                  − 1.490.446 (pagos/amortización línea)
                  −   640.258 (CARGO POR PAGO TC)
                  −    60.335 (PAGO TARJETA DE CREDITO)           = 2.487.653 ✓
```

### ¿Están bien los movimientos? — sí, con evidencia

- 8 cartolas, **48/48 chequeos de cuadratura exactos**, confianza 1.000 en todas.
- Cobertura temporal **contigua sin huecos**: 2025-12-30 → 2026-07-31.
- **El dedup se probó solo en producción:** `CartolaCuentaCorrienteNacionalMensual (2).pdf`
  es el mismo período que `(1).pdf` con otro nombre de archivo → 19 leídas,
  **0 insertadas, 19 duplicadas**. El guard por SHA no aplicaba (archivo distinto), pero
  el `dedup_hash` por movimiento evitó los 19 duplicados. Prueba real del diseño.

### ¿Están bien las clasificaciones? — NO para lo recién importado (hallazgo crítico)

`GET /stats/analytics?period=2026-06` devuelve **"Sin clasificar: 100%"** y lista
`CARGO POR PAGO TC` como mayor gasto y como anomalía. Causa: **el pipeline es manual y
solo clasificó lo que existía cuando se ejecutó.** Los 166 movimientos importados después
entraron con `nature` NULL → cuentan todos como operacionales.

- **V-11 (CRÍTICA de producto, no de código): CORREGIDA con autorización del dueño.**
  Cada importación dejaba los KPIs sin clasificar hasta que alguien recordara ejecutar el
  pipeline. Fix: `ImportService` ejecuta el pipeline sobre la cuenta al cerrar la
  importación, con flag `import.run_pipeline` (default true) y `try/except`: si el
  enriquecimiento falla, la importación YA está escrita y válida, se registra el error y
  se degrada a modo manual. Verificado por test de integración.
- **V-12 (Alta):** confirma M3 — "top comercios" de junio lista personas naturales
  (Vicente Payet, Maximiliano S., Enzo B.). Comercio ≠ contraparte.
- **V-13 (Media):** las anomalías de junio son 4 pagos de tarjeta; desaparecerán al
  clasificar, pero muestran que el detector opera sobre datos sin naturaleza asignada.

### Riesgo nuevo: cuenta de Avícola Limache

Al importar las cartolas de la empresa como segunda cuenta, **cada aporte aparecerá dos
veces**: como `asset` saliendo de la cuenta personal y como abono entrando en la de la
empresa. La vista "Todas las cuentas" sumaría ambos lados. Mitigación inmediata: analizar
siempre con el selector de cuenta. Solución real: reconciliación multi-cuenta (Fase 3).

## 7. Deuda técnica priorizada

*(ídem — clasificación Crítica/Alta/Media/Baja)*

## 8. Retrospectiva Sprint 3

*(documento final, tras cerrar §4–§7)*
