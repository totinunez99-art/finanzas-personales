# 22 — Resolution Pipeline

> Estado: **Implementado (Sprint 3, Bloque 3)** · Creado: 2026-07-13
> Una sola tubería de enriquecimiento. La IA será un resolver más, sin privilegios.

## 1. Contrato único (requisito del dueño)

Todo resolver implementa la MISMA interfaz (`resolution/base.py`):

```python
class Resolver(Protocol):
    name: str
    def prepare(ctx)                    # caches/semillas, idempotente
    def resolve(tx, ctx) -> ResolutionResult   # PROPONE; no muta ni emite
    def on_applied(tx, ctx, result)     # efectos post-aplicación (hits, ADR-008)
```

`ResolutionResult`: cambios propuestos, confianza, explicación (factores),
evidencias, eventos a emitir, duración (cronometrada por el pipeline) y
skipped_reason. Separar "proponer" de "aplicar" es lo que hace posible el
dry-run universal y la auditoría uniforme.

## 2. El pipeline (`resolution/pipeline.py`)

- Ejecuta uno, varios o todos los resolvers **sin tocar su código**:
  `run(session, user, resolvers=["merchant"])` / `["category"]` / `None` (orden configurado).
- **Orden configurable** vía flag `resolution.order` (docs/11), CSV de nombres.
  Nombres desconocidos → `ConfigError` explícito. Sin dependencias implícitas: si pones
  category antes que merchant, corre igual — y las reglas merchant_exact simplemente no
  encontrarán evidencia (testeado).
- El pipeline —no los resolvers— aplica cambios, emite eventos (con duration_ms),
  y produce el reporte por etapa (applied/skipped/no_change/total_ms + muestras en dry-run).
- Encadenamiento real: category ve el merchant que la etapa anterior resolvió EN LA
  MISMA corrida (testeado con COPEC→Combustible).

## 3. Registry

`merchant` y `category` implementados; `recurring`, `subscription`, `anomaly`, `ai`
existen como stubs del mismo contrato (skipped_reason="no implementado aún") — el
orden puede nombrarlos desde hoy y su implementación futura no toca el pipeline.

## 4. Category Resolver (sobre ADR-008, como estaba diseñado desde Fase 1)

- Semillas versionadas: 22 categorías chilenas (expense/income/transfer) + 31 reglas
  `system_seed` (merchant_exact para comercios resueltos, description_contains para
  patrones como ARRIENDO/SUELDO/CARGO POR PAGO TC/TRASPASO A:/DE:).
- Cada asignación: `ClassificationDecision` (decided_by=rule, rule_id, confianza,
  is_current) con supersede encadenado + denormalización en la transacción + evento
  `transaction.classified` con explicación. **Decisión del usuario: intocable** (testeado).
- Idempotente: re-ejecutar no crea decisiones nuevas. Dry-run: cero escritura (testeado).
- Confianzas: tabla de constantes por (origen, matcher) — mismas filosofía que docs/21.

## 5. Ajustes al Merchant Resolver (autoauditoría pre-código, exigida)

Deuda B2 detectada y pagada: iterar/aplicar/emitir vivían en `backfill()` —
habrían duplicado el bucle del pipeline. Ahora: motor puro intacto en
`merchant_resolver.py`, adaptado por `MerchantStage`, y `backfill()` DELEGA en
`pipeline.run(resolvers=["merchant"])` conservando firma y respuesta (API y página
Comercios sin cambios). ImportService: intacto.

## 6. Decisiones y limitaciones

- "Pago de Tarjeta" y transferencias se clasifican con kind=transfer; los KPIs e
  Insights aún NO excluyen transfers del gasto — refinamiento anotado para B4 (si no,
  pagar la TC contaría doble cuando existan cartolas de TC).
- Las reglas no validan signo (INTERES cargo se clasificaría Intereses/income);
  aceptado en MVP, la corrección del usuario y la fase IA lo pulen.
- El pipeline corre bajo demanda (botones en Administración con dry-run). Integrarlo
  post-importación automática = decisión pendiente (tocaría ImportService: prohibido
  este sprint).
