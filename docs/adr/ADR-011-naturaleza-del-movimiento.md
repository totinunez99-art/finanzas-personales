# ADR-011 — Naturaleza del movimiento (reemplaza el flow binario)

Fecha: 2026-07-27 · Estado: **Aceptado** · **Sustituye a ADR-010** (que queda vigente en
su principio —una sola fuente de verdad para el filtro financiero— y superado en su
dominio de valores).

## Contexto

ADR-010 modeló el flujo como binario: `operational | internal`. La validación con 114
movimientos reales (docs/24 §6) lo refutó cuantitativamente: **1 de 33 movimientos
internos detectados (3%)**, y una distorsión medida de $1.768.886 contados como ingreso y
$2.325.626 como gasto que en realidad eran deuda. La causa no fue falta de reglas: fue
falta de un **concepto**. Un giro de línea de crédito aumenta el efectivo y la deuda a la
vez; no es ingreso, no es gasto y tampoco es traspaso entre cuentas propias. No había
dónde ponerlo.

## Decisión

`transactions.flow` se reemplaza por `transactions.nature`, con catálogo cerrado de siete
valores. El **signo del monto** aporta la dirección, evitando duplicar valores:

| Naturaleza | ¿Cambia el patrimonio? | Ejemplo real |
|---|---|---|
| `expense` | Sí (baja) | Supermercado |
| `income` | Sí (sube) | Honorarios |
| `finance_cost` | Sí (baja) | Interés e impuesto de línea de crédito |
| `debt` | No | Giro (+) y pago (−) de línea o tarjeta |
| `lending` | No | Préstamo a un familiar (−) y su devolución (+) |
| `asset` | No | Venta del vehículo (+) |
| `internal` | No | Traspaso entre cuentas propias, pago de tarjeta propia |

- **La naturaleza ES el `kind` de la categoría.** No se agrega motor ni tabla: se amplía
  el dominio de `categories.kind` (y su ancho a 16). El `CategoryStage` existente hace la
  detección; `NatureStage` (antes `FlowStage`) solo deriva.
- **`operational_condition()` sigue siendo la única fuente de verdad** del filtro
  financiero: ahora `nature IS NULL OR nature IN (expense, income, finance_cost)`.
  Reporting, insights y analytics no cambian su lógica, solo heredan la nueva definición.
- **NULL = sin clasificar = visible.** Se mantiene la regla de honestidad de ADR-010.

## Alternativas descartadas

1. **Agregar solo `financing` al binario.** Resolvía el 100% del monto de línea de crédito
   pero dejaba fuera préstamos personales, venta de activos y ámbito de negocio, los tres
   presentes en los datos reales. Se rechazó por obligar a una segunda migración conocida
   de antemano.
2. **Contabilidad de doble entrada.** Correcta por construcción, pero obliga al usuario a
   razonar con asientos y multiplica la complejidad de toda la UI. Se le toma prestado su
   principio (separar movimientos de resultado de movimientos de balance) sin su aparato.

## Decisiones de criterio tomadas por el dueño (2026-07-27)

- **Giro de cajero → `expense`** en categoría "Efectivo sin detalle": el consumo se
  muestra aunque no se conozca su destino. Se prefirió visibilidad sobre precisión.
- **Pago de tarjeta propia → `internal`** (no `debt`) mientras la tarjeta sea una cuenta
  importada del sistema, para evitar doble conteo hasta que exista reconciliación.
- **`lending` y `asset` se incluyen desde la Fase 1**, pese a justificarse con pocos
  movimientos: su costo marginal es una entrada de catálogo.

## Consecuencias

- (+) Los KPIs pasan a tener definición defendible: *gasto = expense + finance_cost*.
- (+) Habilita preguntas nuevas sin trabajo adicional: cuánta deuda se tomó en el mes,
  cuánto me deben. Base de la Fase 3 (patrimonio).
- (+) Corrige por construcción el bug B1 de docs/24: "Intereses" pasa a `finance_cost`,
  de modo que un interés pagado deja de contarse como categoría de ingreso.
- (−) Más naturalezas = más criterio al clasificar; la cobertura automática debe medirse
  tras la primera ejecución real (proyección ~90%, **no** promesa).
- (−) Migración destructiva de `flow` (era 100% NULL en producción; downgrade lo recrea).
- (−) `lending` y `asset` no tienen reglas automáticas: dependen de que el usuario enseñe
  la contraparte una vez (mecanismo ADR-008). Deliberado — sembrar nombres de personas
  reales en el código sería un error de privacidad.
- Caso borde no resuelto: traspasos entre cuentas propias en bancos distintos siguen
  requiriendo reconciliación multi-cuenta (ADR-010 §7 sigue vigente).
