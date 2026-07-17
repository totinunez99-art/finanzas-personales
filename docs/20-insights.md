# 20 — Motor de Insights

> Estado: **Implementado (Sprint 3, Bloque 1)** · Creado: 2026-07-09
> Núcleo del futuro Copiloto Financiero. Sin IA: reglas de negocio deterministas.

## 1. Principios (no negociables)

1. **Determinista y reproducible:** cada insight nace de una consulta SQL descrita en su
   campo `explanation`. Cualquiera puede re-ejecutarla y obtener el mismo número.
2. **Evidencia o silencio:** cada generador declara umbrales como CONSTANTES visibles
   (`MIN_CARGOS_CONCENTRACION=5`, `MIN_CARGOS_DIA_SEMANA=10`, `MIN_APARICIONES_COMERCIO=3`,
   `MIN_DIAS_PROMEDIO=5`, `MIN_TX_MES_ANTERIOR=3`). Bajo el umbral → `None`, jamás una
   conclusión débil. Mes sin datos → lista vacía.
3. **Una moneda por insight** (el motor genera un contexto por moneda presente).
4. **Sin recomendaciones:** observaciones verificables. Las recomendaciones llegarán en
   la fase IA, construidas SOBRE estos insights.

## 2. Contrato

`Insight`: `id` (estable: `tipo:período:moneda`, idempotente entre ejecuciones),
`type` (comparison/average/concentration/pattern/frequency/alert), `title`,
`description`, `severity` (info/notable/warning), `priority` (orden), `currency`,
`data` (números exactos usados, formato canónico), `explanation` (fórmula+filtros).

## 3. Generadores del Bloque 1

| id | Observación | Umbral de evidencia |
|---|---|---|
| flujo_negativo | gastos > ingresos del período | ≥3 movs |
| gasto_vs_mes_anterior | delta % contra mes previo | mes previo con ≥3 cargos y gasto >0 |
| concentracion_top3 | % del gasto en las 3 mayores compras | ≥5 cargos y pct ≥30% |
| promedio_diario | gasto/días transcurridos | ≥5 días con datos |
| compras_vs_mes_anterior | más/menos cargos que el mes previo | ídem comparación |
| comercio_frecuente | comercio con más apariciones | ≥3 apariciones con merchant identificado |
| dia_mas_caro | fecha con mayor gasto | ≥5 cargos |
| dia_semana_gasto | día de semana con mayor gasto acumulado | ≥10 cargos |

Agregar un generador = una función `(_Ctx) -> Insight | None` + registrarla en
`GENERATORS`. Los insights de categorías/comercios enriquecidos llegan con los
Bloques 2-3 (merchant resolver y reglas) sin tocar el motor.

## 4. Decisiones de severidad

`warning`: requiere acción de atención (flujo negativo; gasto +25% m/m).
`notable`: patrón relevante (concentración ≥50%; delta ≥10%). `info`: contexto.
Umbrales revisables con uso real — están en un solo lugar.

## 5. Política de gates actualizada (sesión 14, decisión del dueño)

**Los Quality Gates bloquean el MERGE del sprint, no el desarrollo**, salvo dependencia
técnica directa. Registrado también en docs/19.

## 6. Revisión crítica

- **Riesgo:** umbrales actuales son juicio, no estadística — con 3-6 meses de datos se
  recalibran (están centralizados a propósito).
- **Limitación:** `comercio_frecuente` solo ve movimientos con `merchant` poblado (hoy:
  hints del parser Edwards); el Bloque 2 (resolver) ampliará la cobertura y este mismo
  insight mejorará sin cambios.
- **Caso borde cubierto:** mes en curso usa días transcurridos (no divide por 30 días
  vacíos); mes futuro produce silencio.
