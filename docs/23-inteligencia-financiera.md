# 23 — Centro de Inteligencia Financiera y Normalización de Flujos

> Estado: **Implementado (Sprint 3, Bloque 4)** · Creado: 2026-07-13

## 1. Revisión arquitectónica previa (exigida por el dueño)

**¿ResolutionResult → contexto enriquecible? NO.** `ResolutionContext` ya viaja por el
pipeline (caches compartidos) y las etapas ya se comunican por el canal correcto: la
transacción. Fusionar contratos degradaría la auditabilidad por etapa. **Pero la
revisión destapó un defecto real:** en dry-run los cambios no se aplicaban → la etapa
category no veía el merchant propuesto → simulación subestimada. **Fix (10 líneas, no
un rediseño):** en dry-run el pipeline aplica todo dentro de un **SAVEPOINT** que
revierte al final — encadenamiento idéntico al real, cero persistencia garantizada por
la DB (cambios, decisiones, eventos y semillas incluidos). Verificado por test.

## 2. Normalización financiera (etapa `flow` del pipeline)

- Tercera etapa del orden por defecto (`merchant,category,flow`). Marca cada
  transacción `operational` o `internal` (columna persistida, migración 0005).
- Derivación determinista: categoría `kind=transfer` → internal. Cubre: **Pago de
  Tarjeta, Transferencias entre Cuentas, Reversos y Ajustes** (categoría+reglas nuevas
  REVERSA/ANULACION en la semilla).
- **Única fuente de verdad:** `operational_condition()` en `flow_stage.py`; reporting,
  insights y analytics la importan — cero lógica duplicada. Regla honesta: flow NULL o
  sin categoría = operational (lo no clasificado se MUESTRA como gasto, no se oculta).
- Matiz documentado: `TRASPASO A:/DE:` con TERCEROS es flujo real (así llega el sueldo
  del dueño) y sigue operational vía sus categorías income/expense. Distinguir traspasos
  entre cuentas PROPIAS requiere reconciliación multi-cuenta (fase futura).

## 3. Analytics: respuestas, no gráficos (`core/services/analytics.py`)

Un servicio, una función `overview(period, account, currency)`, once preguntas:
dónde gasto más (categorías + % del gasto), comercios que más reciben, mayores gastos,
día más caro, semanas más costosas, qué creció/disminuyó (delta por categoría vs mes
anterior, sin base → None honesto), % por categoría, flujo de caja diario y acumulado,
gastos anormales, comercios nuevos del período. Endpoint `GET /stats/analytics`.

**Anomalías por regla, no por magia:** cargo > 2.5x el promedio de cargos operacionales
de los 90 días previos, exigiendo ≥10 cargos de historia; sin historia suficiente se
dice explícitamente en vez de inventar. `method_notes` acompaña cada respuesta.

## 4. Página Análisis — disciplina anti-gráfico

Cada sección lleva la PREGUNTA como título. Solo 3 visuales, cada uno con su decisión:
barras de % por categoría (¿dónde recortar?), línea de flujo acumulado (¿me quedo corto
a mitad de mes?), barras semanales (¿qué semanas me desordenan?). Todo lo demás son
tablas con números exactos. "Sin clasificar" aparece como categoría propia: ocultarla
sería mentir sobre la cobertura de clasificación.

## 5. Limitaciones honestas

- Con un mes de datos reales: deltas, anomalías y semanas dicen "sin base/insuficiente"
  hasta importar más cartolas — por diseño, no por falta.
- Analytics es CLP por defecto (parámetro currency para otras); sin conversión entre
  monedas hasta el job de tasas.
- El backfill de flow para datos históricos requiere ejecutar el pipeline una vez
  (botón en Administración) — automático para importaciones futuras cuando el pipeline
  se integre post-import (decisión pendiente, toca ImportService).
