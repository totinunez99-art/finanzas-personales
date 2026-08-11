# 25 — Diseño de la capa conceptual del modelo financiero

> Estado: **APROBADA (alternativa B) e IMPLEMENTADA en Fase 1** · Creado: 2026-07-27
> Decisión formalizada en ADR-011. Fases 2 y 3 pendientes.
> Origen: evidencia cuantitativa de docs/24 §6 (validación con 114 movimientos reales).
> **Este documento NO implica código escrito.** Se escribe para decidir, no para ejecutar.

## 1. El problema, en una frase

El sistema solo sabe si el dinero **entra o sale**; la realidad exige saber **si el
patrimonio cambia o solo cambia de forma**.

### 1.1 Evidencia (febrero 2026, datos reales)

| Movimiento | Hoy se registra como | Qué es en realidad |
|---|---|---|
| Venta del vehículo · $6.200.000 | Ingreso | Cambio de forma: auto → dinero. Patrimonio igual |
| Giros de línea de crédito · $1.768.886 | Ingreso | Deuda tomada. Patrimonio BAJA |
| Pagos a línea de crédito · $2.325.626 | Gasto | Deuda pagada. Patrimonio SUBE |
| Devolución del préstamo del padre · $900.000 | Ingreso | Se extingue una cuenta por cobrar |
| Préstamo entregado al padre · $1.500.000 | Gasto | Nace una cuenta por cobrar. No es consumo |
| Intereses línea de crédito · $23.990 | Ingreso (bug) | Costo financiero: SÍ es gasto real |

De los $9.234.964 rotulados "ingreso" en febrero, la mayor parte no lo es. **Ningún KPI
del dashboard es financieramente válido mientras exista este vacío conceptual.**

### 1.2 Por qué no se arregla con reglas

Una regla asigna una categoría; las categorías existentes solo tienen tres naturalezas
(`expense`, `income`, `transfer`). Un giro de línea de crédito no es ninguna de las tres:
no hay dónde ponerlo. Escribir reglas sobre este modelo produce **precisión aparente
sobre una representación equivocada** — el peor resultado posible, porque el error deja
de ser visible.

## 2. Requisitos que debe cumplir el diseño

1. Distinguir movimientos que **cambian el patrimonio** (gasto, ingreso, costo
   financiero) de los que solo lo **cambian de forma** (deuda, préstamos, activos,
   traspasos, efectivo).
2. Representar deuda en ambas direcciones: con el banco (línea, tarjeta) y con personas.
3. Separar actividad **personal** de **negocio** (caso Cristóbal Merino).
4. No romper lo que ya funciona: parser, dedup, pipeline, auditoría ADR-008/009.
5. Ser explicable a una persona no contadora, en la propia UI.
6. Admitir "no sé": lo no clasificado debe seguir mostrándose, nunca ocultarse.
7. Migrar los 114 movimientos ya importados sin pérdida ni reimportación.

## 3. Alternativas

### A. Mínima — agregar `financing` al flow actual

`flow ∈ {operational, internal, financing}`; nueva categoría kind `financing`.

- **Ventajas:** cambio más pequeño posible (1 migración, 1 archivo); resuelve el 100% del
  problema de línea de crédito, que es el de mayor monto ($4.094.512).
- **Desventajas:** deja fuera 3 de los 4 vacíos detectados — la venta del auto seguiría
  siendo "ingreso", los préstamos del padre seguirían siendo gasto/ingreso, y el negocio
  seguiría mezclado. Sabemos hoy que quedará corto: elegirla es aceptar rehacer la
  migración en pocos meses.

### B. Naturaleza del movimiento explícita *(recomendada)*

Se sustituye el `flow` binario por una **naturaleza** de catálogo cerrado, y el signo del
monto aporta la dirección (no se duplican valores):

| Naturaleza | Qué representa | ¿Cambia patrimonio? | Ejemplo real del dueño |
|---|---|---|---|
| `expense` | Consumo | Sí (baja) | Supermercado, combustible |
| `income` | Ingreso genuino | Sí (sube) | Honorarios, sueldo |
| `finance_cost` | Costo del dinero | Sí (baja) | Intereses, impuesto, comisiones |
| `debt` | Deuda con instituciones | No | Giro de línea (+) / pago de línea (−) |
| `lending` | Préstamos con personas | No | Padre: entrega (−) / devolución (+) |
| `asset` | Compra/venta de bienes | No | Venta del auto (+) |
| `internal` | Entre cuentas propias | No | Traspaso propio, giro de cajero |

Más una dimensión **ortogonal** `scope ∈ {personal, business}` (defecto `personal`), y la
separación **comercio ≠ contraparte** (M3 de docs/24).

- **Ventajas:** cubre los cuatro vacíos con evidencia real; los KPIs quedan definibles sin
  ambigüedad (*gasto del mes = expense + finance_cost*; *ingreso = income*); habilita sin
  trabajo extra dos preguntas que hoy no puedes responder — "¿cuánta deuda tomé este mes?"
  y "¿cuánto me deben?"; **reutiliza toda la arquitectura existente** (ver §4).
- **Desventajas:** siete valores exigen más reglas y más criterio; hay casos legítimamente
  ambiguos (§6); requiere migración de datos y tocar reporting, insights, analytics y UI.

### C. Contabilidad de doble entrada

Cada movimiento como asiento contra cuentas de activo/pasivo/patrimonio/resultado.

- **Ventajas:** correcto por construcción; permite patrimonio neto exacto.
- **Desventajas:** obliga al usuario a pensar como contador, reescribe el modelo completo
  y multiplica la complejidad de toda pantalla. **Rechazada** para uso personal — aunque
  se le toma prestado su principio central: separar movimientos de *resultado* de
  movimientos de *balance*, que es exactamente lo que hace B con menos aparato.

## 4. Recomendación: B, y por qué es más barata de lo que parece

La decisión de ADR-010 —*una sola fuente de verdad para el filtro financiero*— es la que
abarata este cambio. Concretamente:

- `operational_condition()` es el **único** lugar donde se define qué cuenta en las
  estadísticas. Cambia ahí y cambian reporting, insights y analytics a la vez.
- La detección **reutiliza el motor de reglas actual**: basta ampliar el dominio de
  `categories.kind` a las siete naturalezas. Categorías nuevas: "Línea de Crédito"
  (`debt`), "Intereses y Comisiones" (`finance_cost`), "Préstamos Personales"
  (`lending`), "Compra/Venta de Bienes" (`asset`). **Cero tablas nuevas, cero motor nuevo.**
- `FlowStage` pasa a ser `NatureStage`: misma etapa, mismo contrato, más valores. El
  pipeline no se entera.
- La corrección manual ya existe: enseñar "Christian Nunez → Préstamos Personales" crea
  una regla de usuario permanente con el mecanismo de ADR-008 ya construido.

Es decir: **el diseño de los Sprints 2 y 3 aguanta el cambio conceptual sin rediseño.**
Esa es la prueba real de que la arquitectura era correcta.

## 5. Plan por fases (para decidir alcance, no para ejecutar hoy)

- **Fase 1 — Naturaleza.** Migración `transactions.nature`; ampliar `kind`; semillas y
  reglas para línea de crédito, tarjeta, costos financieros, efectivo; `NatureStage`;
  `operational_condition()` = `nature ∈ (expense, income, finance_cost)` o NULL; KPIs y UI
  hablando de "gasto real" vs "movimientos de deuda". Migración de los 114: re-ejecutar el
  pipeline (no se reimporta nada).
- **Fase 2 — Contraparte y ámbito.** Separar `counterparty` de `merchant` (deja de haber
  personas en "top comercios"); `scope` personal/negocio con reglas por contraparte.
- **Fase 3 — Balance.** Con deuda y préstamos ya marcados: saldo de deuda, cuánto te
  deben, y evolución de patrimonio. Es la primera capacidad de *copiloto* propiamente tal:
  no describe el pasado, informa una decisión.

## 6. Decisiones abiertas que requieren tu criterio

1. **Pago de tarjeta de crédito propia: ¿`internal` o `debt`?** Si la tarjeta se importa
   como cuenta aparte, el pago aparece en ambas cartolas y marcarlo `debt` arriesga doble
   conteo hasta que exista reconciliación. *Recomendación: `internal` mientras la tarjeta
   sea una cuenta del sistema; `debt` si no se importa.*
2. **Giro de cajero: ¿`internal` o `expense`?** El dinero no se consumió al salir del
   cajero, pero rara vez sabrás en qué se fue. *Recomendación: `internal`, aceptando que
   ese gasto queda invisible; la alternativa honesta es una categoría "Efectivo sin
   detalle" visible en los reportes.*
3. **Venta del auto: ¿aparece en el mes o se excluye?** *Recomendación: `asset`, visible
   como movimiento destacado pero fuera del ingreso, para no arruinar los promedios.*
4. **Alcance del Sprint 4: ¿solo Fase 1, o Fases 1+2?**

## 7. Revisión crítica de esta propuesta

- **Riesgo de sobre-ingeniería:** `asset` y `lending` se justifican con 3 y 4 movimientos
  reales respectivamente. Si tu vida financiera no vuelve a producirlos, serán valores
  muertos. *Mitigación:* el catálogo es una lista de valores, no infraestructura; su costo
  marginal es casi nulo. Aun así, si prefieres, pueden diferirse a la Fase 2 sin bloquear
  el resto.
- **Riesgo de carga de clasificación:** más naturalezas = más decisiones para ti. Si la
  cobertura automática no sube del ~62% actual, el modelo será más correcto pero más
  trabajoso. *Mitigación:* las reglas nuevas (línea de crédito, tarjeta, costos) atacan
  justo los 30+ movimientos hoy no clasificados; la proyección es subir a ~90%, pero es
  **proyección y debe medirse**, no una promesa.
- **Riesgo de migración:** los 114 movimientos actuales quedan con `nature` NULL hasta
  ejecutar el pipeline. Se comportan como operacionales (honesto, visible), no se pierden.
- **Caso borde no resuelto:** transferencias entre tus propias cuentas en bancos distintos
  siguen sin ser detectables automáticamente hasta la reconciliación multi-cuenta
  (ADR-010 §7). El sistema seguirá necesitando que se lo enseñes una vez.
- **Lo que este diseño NO resuelve:** cuotas y compras en cuotas, moneda extranjera y UF,
  e inversiones. Están fuera del alcance declarado y deben tener su propio análisis.
- **Si finalmente eliges A:** es una decisión defendible si tu prioridad es ver KPIs
  correctos esta semana. Solo debe tomarse sabiendo que la evidencia ya demostró que
  quedará corta, y que la segunda migración costará más que la primera.
