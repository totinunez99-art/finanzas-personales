# ADR-010 — Clasificación de flujo financiero (operational / internal)

Fecha: 2026-07-17 · Estado: **Aceptado** (origen: Sprint 3 Bloque 4, formalizado a petición del dueño)

## Contexto

Las estadísticas mentían por construcción: un pago de tarjeta de $500.000 aparecía como
"gasto" del mes, cuando es dinero moviéndose entre bolsillos propios. El Centro de
Inteligencia Financiera (docs/23) exige separar **flujo real** (gasto/ingreso operacional)
de **movimiento interno** (pago de tarjeta, traspasos entre cuentas propias, reversos)
antes de calcular cualquier KPI, insight o analítica. La pregunta arquitectónica: ¿dónde
vive esa separación y bajo qué reglas?

Implementación: `FlowStage` (tercera etapa del Resolution Pipeline, docs/22), columna
persistida `transactions.flow` (migración 0005), filtro canónico `operational_condition()`.

## Alternativas evaluadas

1. Filtrar por nombre de categoría en cada consulta de reporting ("WHERE category NOT IN
   ('Pago de Tarjeta', ...)"): rechazada — lógica duplicada en N consultas, strings mágicos,
   imposible de auditar, se rompe al renombrar una categoría.
2. Un flag booleano en la categoría consultado en tiempo de lectura (sin columna en la
   transacción): rechazada — el estado de cada transacción quedaría implícito y cambiaría
   retroactivamente al editar la categoría, sin traza de cuándo ni por qué; además obliga a
   un JOIN en cada estadística.
3. Fusionar la lógica dentro de `CategoryStage`: rechazada (ver pregunta 2).
4. **(Elegida)** Etapa independiente `flow` del pipeline que persiste
   `transactions.flow ∈ {operational, internal}` con decisión auditada por evento, y una
   única condición SQL exportada que todo consumidor importa.

---

## Las siete preguntas

### 1. ¿Por qué Flow es una etapa independiente del pipeline?

Porque cumple los tres criterios que definen una etapa (docs/22): tiene una
responsabilidad única (decidir si una transacción cuenta o no en estadísticas), produce
un `ResolutionResult` auditable con explicación y evento propio (`flow.normalized`), y
debe poder ejecutarse aisladamente (backfill de datos históricos: "corre solo flow sobre
todo lo importado antes de la migración 0005"). Además el pipeline garantiza el
encadenamiento correcto: flow corre *después* de category en el orden por defecto
(`merchant,category,flow`), de modo que ve la categoría recién propuesta — incluso en
dry-run, gracias al SAVEPOINT (docs/23 §1). Si fuera lógica incrustada en reporting, no
habría traza, ni backfill selectivo, ni simulación.

### 2. ¿Por qué no forma parte de Category?

Porque responden preguntas distintas con semánticas de persistencia distintas:

- **Category responde "¿qué es este movimiento?"** (semántica del gasto). Persiste
  `ClassificationDecision` con cadena de supersede y protección de decisiones de usuario
  (ADR-008).
- **Flow responde "¿cuenta este movimiento en mis estadísticas?"** (alcance contable).
  Hoy es una *derivación* determinista de la categoría — no una decisión nueva — y por
  eso no crea `ClassificationDecision`: duplicaría la auditoría de una misma decisión.

El argumento decisivo es evolutivo: las señales futuras de flow **no son categóricas**.
Detectar un traspaso entre cuentas propias requiere reconciliación multi-cuenta (calzar
montos opuestos ±N días entre dos cuentas); calzar una reversa con su cargo original
requiere matching por monto+fecha. Nada de eso es "clasificar en una categoría". Si flow
viviera dentro de Category, esa lógica de reconciliación contaminaría un resolver que hoy
es puro pattern-matching. Separados, cada uno evoluciona sin arrastrar al otro.

### 3. ¿Qué reglas utiliza exactamente?

Una sola regla de derivación, determinista (confianza 1.00 por definición):

```
categoría del movimiento tiene kind = 'transfer'  →  flow = 'internal'
cualquier otro caso (incl. sin categoría)         →  flow = 'operational'
```

Las categorías `kind=transfer` en la semilla son tres: **Pago de Tarjeta**,
**Transferencias entre Cuentas** y **Reversos y Ajustes**. Las alimentan estas reglas de
clasificación (tabla `classification_rules`, sembradas por código pero editables en DB):
`CARGO POR PAGO TC` → Pago de Tarjeta; `REVERSA` y `ANULACION` → Reversos y Ajustes
(matcher `description_contains` sobre la descripción normalizada).

El consumo es una única condición SQL, `operational_condition()` en `flow_stage.py`:
`flow IS DISTINCT FROM 'internal'`. La importan reporting, insights y analytics — cero
duplicación. La forma `IS DISTINCT FROM` es deliberada: **NULL cuenta como operacional**.
Lo no procesado por el pipeline se MUESTRA como gasto; ocultarlo maquillaría la cobertura.

Matiz documentado (docs/23 §2): `TRASPASO A:/DE:` con terceros es flujo real (así llega
el sueldo) y queda operational vía sus categorías income/expense. No es un caso perdido:
es la regla aplicándose correctamente.

### 4. ¿Cómo se incorporarán nuevas reglas sin modificar código existente?

Tres niveles, los dos primeros sin tocar código:

1. **Nueva regla de texto** → insertar en `classification_rules` apuntando a una
   categoría `kind=transfer` existente. En la siguiente ejecución del pipeline, category
   asigna y flow deriva. Cero código.
2. **Nuevo tipo de movimiento interno** → crear una categoría con `kind=transfer` (la
   tabla `categories` es del usuario; `FlowStage` lee `kind` en runtime, no tiene nombres
   hardcodeados) + sus reglas. Cero código.
3. **Nuevo mecanismo de derivación** (p. ej. reconciliación multi-cuenta) → sí es código:
   un resolver nuevo o una versión nueva de `FlowStage`, con su propio ADR si cambia el
   contrato. Correcto que lo sea — es un cambio de algoritmo, no de datos.

Limitación honesta: hoy no existe UI para los niveles 1 y 2 (solo el *teach* de comercios
tiene UI); requieren SQL o la futura pantalla de administración de reglas. La
arquitectura ya lo soporta; falta la puerta de entrada.

### 5. ¿Cómo podrá un usuario corregir una clasificación?

**Hoy: indirectamente, vía la categoría.** El usuario corrige la categoría del movimiento
(mecanismo ADR-008: `ClassificationDecision` con `decided_by=user`, intocable para reglas
e IA); en la siguiente ejecución del pipeline, flow re-deriva y sigue a la categoría. La
corrección es durable porque la decisión de usuario nunca es superseded.

**No implementado y documentado como deuda:** un override directo de flow ("esto es
interno" sin cambiar la categoría — ejemplo real: una transferencia enviada a una cuenta
propia en otro banco). Requerirá `flow_source` (paralelo a `merchant_source`) con
precedencia usuario > derivación, misma jerarquía que el resto del sistema. Se difiere
hasta que la reconciliación multi-cuenta lo haga necesario, porque hoy el rodeo (crear
una regla hacia "Transferencias entre Cuentas") cubre el caso.

### 6. ¿Qué porcentaje de decisiones espera automatizar correctamente?

Separando las dos capas, porque prometer un número global sería deshonesto:

- **Derivación categoría→flow: 100% por construcción.** Es determinista; si la categoría
  es correcta, flow es correcto. Los errores de flow son siempre errores de clasificación
  aguas arriba.
- **Detección de movimientos internos (la capa que sí puede fallar):** hipótesis ≥95%
  para cartolas de tarjeta, porque el movimiento interno dominante (pago de la tarjeta)
  llega con string fijo del banco (`CARGO POR PAGO TC` — verificado en la cartola real de
  junio: 1/1 detectado). Reversas/anulaciones también llegan con prefijos estables.

Esto es una **hipótesis a medir, no una promesa**. Métrica definida: proporción de
correcciones de usuario sobre categorías transfer respecto del total de movimientos
internos, calculable desde `classification_decisions` (`decided_by=user` que supersede a
`rule`) — la infraestructura de medición ya existe. Compromiso: registrar el valor real
en docs/19 tras importar tres cartolas reales.

### 7. ¿Cómo se resolverán los casos ambiguos (por ejemplo, transferencias)?

La ambigüedad real es una sola: **una transferencia a un tercero es gasto; la misma
transferencia a una cuenta propia es movimiento interno — y el texto de la cartola no las
distingue.** Resolución en tres tiempos:

1. **Hoy — regla de sesgo declarada:** ante ambigüedad, `operational`. Principio: es
   preferible sobrestimar el gasto mostrando un traspaso propio, que ocultar un gasto
   real marcándolo interno. El error visible se corrige; el invisible se acumula.
2. **Hoy — corrección del usuario:** recategorizar a "Transferencias entre Cuentas"
   (pregunta 5), protegida por ADR-008.
3. **Futuro — reconciliación multi-cuenta** (resolver ya previsto como stub en el
   pipeline): cuando existan ≥2 cuentas importadas, calzar pares (monto opuesto, ventana
   de días, cuentas del mismo usuario) y marcar ambos lados como internal con la
   evidencia del par en el `ResolutionResult`. Las reversas se calzarán igual contra su
   cargo original. Requerirá ADR propio si introduce estado nuevo (tabla de pares).

## Consecuencias

- (+) Un solo punto de verdad SQL; imposible que dashboard e insights discrepen sobre qué
  cuenta como gasto.
- (+) Backfill y simulación gratis por ser etapa del pipeline (botones en Administración).
- (−) Flow depende de la calidad de category: sin categoría no hay detección de internos.
  Aceptado — el fallback (operational, visible) es el lado seguro del error.
- (−) La corrección directa de flow no existe aún; el rodeo vía categoría es funcional
  pero no obvio para un usuario nuevo. Mitigación futura: `flow_source` + UI.
- (−) Ejecutar el pipeline es hoy manual post-import (decisión pendiente que toca
  ImportService); una importación sin pipeline deja flow NULL → todo cuenta como
  operacional hasta el siguiente run. Comportamiento honesto, pero debe documentarse en
  la guía de uso.
