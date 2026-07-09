# 14 — Import Wizard

> Estado: **Implementado (Sprint 1 de Fase 2)** · Creado: 2026-07-06
> Puerta de entrada ÚNICA para archivos de movimientos. Fuentes futuras (XLSX/PDF
> bancarios, API) se suman como parsers; el núcleo no cambia.

## 1. Flujo

```
archivo → ¿PDF cifrado? (fase A, docs/18 §8)
   ├─ sin clave → preview.password_required=true + mensaje de no persistencia
   │              (la clave viaja solo en el request; jamás se loguea ni almacena)
   └─ clave ok (o no cifrado) ↓
        → detección (registry.detect: sniff de cada parser, gana mayor confianza)
   ├─ no reconocido → "Este formato aún no es compatible."
   │                  + registro en unrecognized_files (metadatos, no contenido)
   └─ reconocido → parse (tolerancia cero: ParserError con fila exacta ante duda)
        → PREVIEW: banco, parser, razón, total, muestra (20), duplicados vs DB,
                   ¿archivo ya importado? — NO escribe dominio
        → usuario confirma (cerrar página = cancelar; nada se guardó)
        → IMPORT: batch + transacciones con dedup_hash + intra_day_seq,
                  eventos transaction.imported y batch.completed,
                  contadores auditables en import_batches
```

Dos pasos deterministas sobre el mismo archivo: preview e import parsean por separado
(sin estado de servidor entre pasos; la idempotencia la garantizan `uq(account_id,
file_sha256)` y `uq(account_id, dedup_hash)` en DB, no la memoria del proceso).

## 2. Contratos (actualizados sesión 11)

- **`StatementParser`** (`connectors/statements/base.py`): `sniff()`/`parse()` aceptan
  `password` opcional; `capabilities: ParserCapabilities` declara qué soporta cada
  conector (tipos de archivo, contraseña, metadata, saldos, cuenta).
- **`ImportResult`** (reemplazó a ParsedStatement): transacciones + metadata +
  `ValidationReport` tipado (chequeos con esperado/observado) + `parser_version` +
  `detected_format` + `extraction_confidence` (proporción determinista de señales de
  calidad; fórmula única en `confidence_from_signals`). Validación dura fallida =
  ParserError = nada se importa (doble garantía: parser lanza y el núcleo re-verifica).
- **Trazabilidad**: cada `import_batch` registra versión de parser, formato detectado,
  validación completa (jsonb), saldos inicial/final y confianza (migración 0003).
- **Registro** (`registry.py`): la única lista que se toca al agregar un banco.
- **`ImportService`** (`core/services/import_service.py`): preview/confirm; asigna
  `intra_day_seq` por clave repetida dentro del archivo (docs/03 §4).
- Errores HTTP: 422 archivo inválido · 415 formato no compatible · 409 ya importado ·
  404 cuenta inexistente. Mensajes en castellano, pensados para mostrarse tal cual en la UI.

## 3. Detección de banco/cuenta — estado honesto

- **Banco:** lo declara cada parser (`bank`). Hoy solo existe `generic` (CSV de
  referencia). El conector `bancochile` se construirá cuando existan cartolas reales en
  `golden/originals/` — regla docs/13, sin excepciones.
- **Cuenta:** el CSV de referencia no la identifica → la elige el usuario. Los parsers
  bancarios reales podrán proponerla vía `account_hint` (el contrato ya lo soporta).
- **XLSX/PDF:** el wizard los acepta y responde "formato no compatible" registrándolos.
  Soporte real llega con los parsers bancarios (pdfplumber/openpyxl se agregan entonces,
  no antes).

## 4. Formato CSV de referencia (puente inmediato)

```
fecha;descripcion;monto[;moneda]
2026-06-01;COMPRA LIDER;-45.990
```
Fechas: `YYYY-MM-DD`, `DD-MM-YYYY`, `DD/MM/YYYY`. Montos: signo explícito; reglas
deterministas para separadores chilenos (ver `parse_amount`, con tests exhaustivos).
Cargo negativo, abono positivo. Moneda vacía = moneda de la cuenta.

## 5. Checklist para agregar un parser bancario (obligatoria)

1. Cartolas reales en `golden/originals/statements/<banco>/` (mínimo 2 meses).
2. Anonimizar → casos en `golden/cases/statements/<banco>/` (≥1 normal, ≥1 borde, ≥1 error).
3. Implementar `<banco>_<formato>.py` con `sniff` específico (confianza > generic).
4. Registrarlo en `registry.py`.
5. `pytest tests/golden` verde + `verify_no_leaks` limpio.
6. Actualizar esta página (§3) y MASTER_PROJECT.
**Sin pasos 1-2 no hay parser** — un parser sin golden es un generador de datos corruptos con buena intención.

## 6. Revisión crítica

- **Riesgo:** el archivo se sube dos veces (preview + confirm); si el usuario edita el
  archivo entre ambos, importa la versión nueva. Aceptable: el preview del contenido
  final siempre es el que se importa (re-parseo determinista), jamás uno obsoleto.
- **Limitación:** dedup por hash no detecta la misma compra con glosa distinta entre
  archivos (eso es reconciliación, fase siguiente; docs/03 §5).
- **Limitación consciente:** carrera entre dos imports simultáneos del mismo archivo la
  resuelve el constraint de DB con error, no con gracia. Mono-usuario: correcto así.
- **Deuda:** respuestas API como dicts sin esquema Pydantic de salida; se formaliza
  cuando la API tenga un segundo consumidor.
