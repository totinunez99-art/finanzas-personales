# 17 — Dashboard Financiero (Sprint 2)

> Estado: **Implementado (Parte A)** · Creado: 2026-07-06

## 1. Estructura de la UI

- **Home (`app.py`):** dashboard financiero — selector de período, métricas del mes
  (ingresos, gastos, saldo neto, movimientos), última importación, botón Importar,
  tabla de movimientos con búsqueda y filtros (compacta; enlace a la vista completa).
- **Importar:** wizard (docs/14), sin cambios.
- **Movimientos:** tabla completa (hasta 1000) + filtro por cuenta + historial de importaciones.
- **Administración:** la antigua pantalla de salud (API, DB, migración, jobs, flags, eventos).

Home y Movimientos comparten `components.py` (filtros y tabla): una sola implementación.

## 2. API

- `GET /transactions`: `q` (búsqueda insensible a tildes/caso vía `description_norm`),
  `date_from/date_to`, `amount_min/amount_max` (sobre **magnitud**), `kind` (cargo/abono),
  `account_id`, paginación. Lógica en `core/services/reporting.py` (testeable, router delgado).
- `GET /stats/summary?period=YYYY-MM`: ingresos/gastos/neto/cantidad **por moneda** +
  última importación. Sin parámetro = mes actual.

## 3. Decisiones y limitaciones documentadas

- **Montos por moneda, jamás sumados entre monedas:** las métricas principales muestran
  CLP; otras monedas van en un expander separado. Sumar CLP+USD sería un número falso.
  La conversión vía `exchange_rates` llega cuando exista el job de tasas (fase siguiente).
- **Filtro de monto por magnitud y ciego a moneda:** filtrar "entre 10.000 y 100.000"
  compara |monto| sin distinguir CLP de USD (test lo documenta). Aceptado en MVP;
  se refina junto con la conversión de monedas.
- **Categoría:** siempre "Sin clasificar" en este sprint (la clasificación es de la fase IA).
- **"Este mes" = mes calendario por `posted_at`**, no ventana móvil de 30 días.

## 4. Pendiente de este sprint (Parte B — bloqueada por muestras)

Conector **Banco Edwards (PDF)**: espera cartolas reales en
`golden/originals/statements/edwards/`. Nacerá con la checklist de docs/14 §5
(anonimización → casos golden → parser → registro). Requerirá agregar `pdfplumber`
(dependencia justificada: no hay parseo de PDF sin ella; se agrega junto al parser,
no antes — regla docs/12 §3.3).
