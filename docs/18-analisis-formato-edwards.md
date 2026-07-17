# 18 — Análisis del Formato: Cartola Cuenta Corriente Banco Edwards (PDF)

> Estado: **IMPLEMENTADO (sesión 13, bloque 2)** — parser `edwards_cc_pdf` v1.0.0 validado
> contra la cartola real (19 tx, cuadratura dual exacta, confianza 1.0). Hallazgo nuevo
> incorporado durante la implementación: el encabezado de la tabla tiene una SEGUNDA
> línea ("DIA/MES ... O CARGOS O ABONOS") que debe saltarse (§9.11 implícito).
> Ajustes aprobados: ImportResult + ValidationReport tipado + ParserCapabilities +
> extraction_confidence determinista + golden principal basado en reales anonimizados
> (sintéticos solo como complemento).
> Creado: 2026-07-08 · Base: 1 cartola real (junio 2026, 1 página) analizada con
> pdfplumber 0.11 y pypdf 6 sobre el archivo original.
> ⚠ Todos los valores de ejemplo en este documento son FICTICIOS (el doc se versiona en git).

## 1. Tipo de PDF

**Texto nativo con cifrado.** Generado por sistema documental **COLDview** (backend
Banco de Chile/Edwards) con OpenPDF 1.3.32. Una imagen embebida (logo). No es escaneado:
el 100% del contenido transaccional es texto extraíble con coordenadas.

**Hallazgo crítico:** el PDF está **cifrado con contraseña de usuario** (en la muestra:
un número corto definido por el banco/cliente). Sin la clave no se puede leer NI la
metadata. Implicancia de producto: el wizard debe aceptar una contraseña opcional para
PDFs (cambio en `POST /imports/preview` y `POST /imports` + campo en la UI). La clave
jamás se persiste ni se loguea.

## 2. Calidad del texto

Excelente: ~2.200 caracteres/página, sin errores de codificación, tildes correctas,
números con formato chileno consistente (`1.234.567`). pypdf y pdfplumber extraen texto
casi idéntico. No se requiere OCR.

**Trampa detectada:** la extracción de texto plano APLANA las tres columnas numéricas
(cargos / abonos / saldo) en una sola secuencia — un monto aislado en el texto no dice
si es cargo o abono. La clasificación exige coordenadas (ver §13).

## 3. Herramienta recomendada

**pdfplumber** (extracción posicional de palabras) + **pypdf** (descifrado y metadata) +
`pycryptodome` (dependencia de pypdf para AES). OCR: innecesario.
`extract_table()` de pdfplumber: **inservible aquí** (probado: estrategia default
devuelve 4 filas basura; estrategia "text" 54×15 con ruido) — la tabla no tiene líneas
verticales de guía. La unidad de trabajo es `extract_words()` con x/y.

## 4. Tablas detectadas (5 bloques)

1. **Encabezado de cuenta:** titular, email, línea de crédito (aprobado/utilizado/disponible/vencimiento).
2. **Identificación:** ejecutivo, sucursal, teléfono, N° cuenta (enmascarado `XXXXXXXX####`), moneda, N° cartola, N° página ("1 DE N"), período DESDE/HASTA.
3. **Tabla principal de movimientos** (ver §5).
4. **Resumen de retenciones:** retención a 1 día / a más de 1 día / saldo disponible.
5. **Resumen por categoría:** depósitos, cheques, otros abonos, otros cargos, giros cajero, impuestos.

Además, **metadata estructurada del PDF** (claves `/CVQT_*` de COLDview): N° cuenta
completo, período (`FECHADESDE/FECHAHASTA` en `YYYYMMDD`), saldo disponible, N° cartola,
totales por categoría (mismos valores del bloque 5, en formato entero de 12 dígitos) y
4 checksums MD5 de los arreglos de transacciones (`TRX_DETALLE`, `TRX_MONTOS`,
`TRX_SUC`, `TRX_DATE` — algoritmo de entrada desconocido, no verificable por ahora).
**Esta metadata es una segunda fuente de verdad para validación (§10).**

## 5. Columnas de la tabla principal

| Columna | Encabezado real | Banda X aprox. (pág. A4 595pt) | Contenido |
|---|---|---|---|
| Fecha | `FECHA DIA/MES` | x≈23-50 | `DD/MM` — **sin año** (§9.1) |
| Detalle | `DETALLE DE TRANSACCION` | x≈60-225 | descripción libre, prefijos estables (`TRASPASO A:/DE:`, `PAGO:`, `CARGO POR...`, `DEP.CHEQ...`, `PRIMA SEGURO...`, `APP-`) |
| Sucursal | `SUCURSAL` | x≈227-300 | `INTERNET`, `CENTRAL`, nombre de oficina |
| N° Docto | `N° DOCTO` | x≈309-340 | casi siempre vacío; presente en depósitos con documento |
| Cargos | `MONTO CHEQUES O CARGOS` | números alineados a la derecha, x1≈395-415 | monto positivo en texto = cargo |
| Abonos | `MONTO DEPOSITOS O ABONOS` | x1≈465-490 | monto positivo en texto = abono |
| Saldo | `SALDO` | x1≈545-575 | saldo del día — **solo en la última fila de cada día** |
| Flag | (sin encabezado) | coordenadas corruptas (§9.6) | `D` (¿deudor/disponible?) tras cada saldo |

Filas especiales: `SALDO INICIAL` (primera, con fecha del inicio de período, solo saldo)
y `SALDO FINAL` (última, solo saldo). No son transacciones: son anclas de validación.

## 6. Mapeo a `transactions` (columnas obligatorias)

| Campo del modelo | Origen | Transformación |
|---|---|---|
| `posted_at` | Fecha `DD/MM` + año del período (metadata `FECHADESDE/HASTA`) | resolución de año con rollover (§9.1) |
| `amount` | columna Cargos → negativo; columna Abonos → positivo | parseo formato chileno (reutiliza `parse_amount`) |
| `currency` | bloque identificación (`MONEDA: PESOS` → CLP) | mapa cerrado; otro valor → ParserError |
| `description_raw` | Detalle, texto íntegro | inmutable |
| `source_ref` | página + índice de fila | |
| `account_hint` | últimos 4 del N° cuenta enmascarado (y cuenta completa desde metadata) | propuesta automática de cuenta en el wizard |

## 7. Información adicional que conviene guardar

- En `ImportBatch`: `period_start/end` (metadata, más confiable que el texto),
  saldo inicial y final (→ **propuesta**: columnas nuevas `opening_balance/closing_balance`
  en `import_batches`, migración 0003 junto al parser), N° de cartola (correlativo del
  banco: detecta cartolas faltantes — si importaste la 6 y la 8, falta la 7).
- `merchant_hint`: extraíble del prefijo del detalle (`PAGO:COPEC` → COPEC;
  `TRASPASO A:/DE:` → contraparte). Barato ahora, útil para la fase de clasificación.
- `installment_raw`: no aplica en cuenta corriente (sí aplicará en cartola TC, formato distinto no analizado).
- Sucursal y N° docto → `payload` informativo, no columnas nuevas.

## 8. Detección automática (sniff)

Problema previo: **un PDF cifrado no expone nada sin contraseña**. Flujo de detección en dos fases:
1. `sniff` fase A (sin clave): extensión `.pdf` + diccionario `/Encrypt` presente →
   respuesta al wizard: "PDF protegido: ingresa la contraseña" (nuevo estado del preview,
   ni 'reconocido' ni 'no compatible').
2. `sniff` fase B (con clave): señales fuertes y baratas, en orden:
   metadata `/Author == "COLDview"` **y** existencia de claves `/CVQT_*` (≥5) →
   confianza 0.98; refuerzo textual: `"Estado de Cuenta"` + `"WWW.BANCOEDWARDS.CL"` o
   `"WWW.BANCOCHILE.CL"` en página 1. La marca (Edwards vs Chile) se distingue por el
   texto de sucursal/URL si llegara a importar; el formato es el mismo sistema COLDview.

## 9. Problemas esperados (catálogo para casos golden)

1. **Año ausente en fechas** (`DD/MM`): resolver contra el período. Cartola diciembre-enero:
   filas de diciembre → año del `FECHADESDE`, filas de enero → año siguiente. Regla:
   asignar el año que mantenga la fecha dentro de `[FECHADESDE, FECHAHASTA]`.
2. **Saldo solo en la última fila del día** → el saldo NO es atributo de la transacción;
   solo se usa para validar el encadenado por día (§10.3).
3. **Multipágina no observado** (muestra = 1 página, dice "1 DE 1"): encabezados
   repetidos por página, posible corte de día entre páginas, ¿SALDO FINAL solo en la
   última? **Se necesita una cartola de ≥2 páginas antes de congelar el parser.**
4. **Detalle largo**: ¿trunca o envuelve a segunda línea? No observado. Si envuelve,
   la reconstrucción por `top` debe fusionar líneas sin fecha con la fila anterior.
5. **Montos que invaden bandas**: valores right-aligned desbordan el ancho del
   encabezado → los límites de banda deben calcularse como puntos medios entre clusters
   de valores, no como el bounding box del título.
6. **Flags `D` con coordenadas corruptas** (x≈56.693 en una página de 595pt — bug del
   generador): no usar posicionalmente; capturar por regex o ignorar.
7. **Cartola sin movimientos** (solo saldos): caso golden obligatorio.
8. **Cambio silencioso de layout por parte del banco**: mitigado por §10 (la cuadratura
   detecta pérdida de filas) y R-02.
9. **Cuenta en USD u otra moneda**: `MONEDA:` distinto de PESOS → error explícito hasta
   tener muestra real.
10. **Misma compra duplicada el mismo día** (dos PAGO:COPEC reales en la muestra):
    cubierto por `intra_day_seq` — el parser debe PRESERVAR el orden del PDF.

## 10. Reglas de validación de una importación (todas duras salvo indicación)

1. **Cuadratura global:** `SALDO INICIAL + Σabonos − Σcargos == SALDO FINAL`.
   Verificada en la muestra real (exacta al peso). Fallo → batch `failed`, nada se inserta.
2. **Cuadratura contra metadata:** `Σabonos == CVQT_DEPOSITOS + CVQT_OTROSABONOS` y
   `Σcargos == CVQT_OTROSCARGOS + CVQT_CHEQUES + CVQT_GIROS + CVQT_IMPUESTOS`;
   `SALDO FINAL == CVQT_SALDODISPONIBLE` (cuando no hay retenciones; con retenciones,
   advertencia en vez de error hasta observar el caso).
3. **Encadenado por día:** el saldo impreso de cada día == saldo acumulado calculado. 
4. **Consistencia de período:** toda fecha resuelta ∈ `[FECHADESDE, FECHAHASTA]`.
5. **Página completa:** "N° DE PAGINA: X DE Y" → se leyeron Y páginas.
6. Toda fila no clasificable como transacción, saldo o pie conocido → ParserError con
   número de fila (tolerancia cero, docs/05 §3).

## 11. Riesgos de mantenimiento

- **El banco controla el layout**: COLDview puede cambiar coordenadas/textos sin aviso.
  Mitigación: bandas calculadas dinámicamente desde los encabezados de cada página (no
  constantes mágicas), cuadratura como red (un desplazamiento de columna rompe la suma
  → error, no datos corruptos), fixtures de regresión por mes.
- **El cifrado puede cambiar** (algoritmo/política). pypdf+pycryptodome cubren RC4/AES actuales.
- **Checksums CVQT_TRX_\*** no verificables (algoritmo desconocido): si algún día se
  descifra su formato, serían la validación definitiva. Anotado como mejora futura.
- **Una sola muestra**: este diseño asume estabilidad mensual sin evidencia. Riesgo
  reducible solo con más cartolas (acción pendiente de Tomás: 2-3 meses más, ideal una multipágina).

## 12. Reutilizable para otros bancos

- Infra de **PDF cifrado** (flujo de contraseña en wizard + API): genérico.
- **Clasificador por bandas X** dinámicas desde encabezados: patrón general de cartolas
  chilenas en PDF (extraer a helper común cuando llegue el segundo banco, no antes).
- `parse_amount` chileno: ya compartido (generic_csv).
- **Resolución de año DD/MM contra período** con rollover: helper común.
- Marco de validación por cuadratura: patrón común (cada banco define sus ecuaciones).
- Banco de Chile "clásico" comparte COLDview → el mismo parser probablemente sirva con
  ajustes mínimos (misma familia de formato).

## 13. Estrategia de parsing (resumen ejecutable)

```
1. pypdf: ¿/Encrypt? → exigir password → decrypt (USER_PASSWORD) → leer metadata CVQT_*
2. sniff (§8) → confianza
3. Por página (pdfplumber):
   a. extract_words() → localizar fila de encabezados (FECHA/DETALLE/.../SALDO)
   b. bandas X = puntos medios entre clusters de encabezados y valores
   c. agrupar palabras por `top` (tolerancia ±2pt) → filas
   d. clasificar fila: encabezado | SALDO INICIAL/FINAL | transacción | pie | desconocida(→error)
   e. por fila de transacción: fecha (año resuelto §9.1), detalle (banda), sucursal,
      docto, monto (banda cargo→negativo / abono→positivo), preservando orden
4. Validaciones §10 → RawTransaction[] + metadatos de batch (saldos, período, N° cartola)
5. ImportService (sin cambios: es un StatementParser más del registry)
```

Cambios de sistema requeridos ANTES del parser (mismo PR): password opcional en
preview/import (API+UI), migración 0003 (`opening/closing_balance` en import_batches),
dependencias `pdfplumber` + `pycryptodome`.

## Pendientes para pasar a implementación

1. **Ratificación de este diseño por el dueño.**
2. **Más muestras**: ≥2 meses adicionales y ojalá una multipágina y una sin movimientos (§9.3, §9.7).
3. Confirmar política de la contraseña en UX: se pide cada vez (no se almacena — recomendado) vs. guardarla cifrada (requiere diseño de secreto adicional; NO recomendado en MVP).
