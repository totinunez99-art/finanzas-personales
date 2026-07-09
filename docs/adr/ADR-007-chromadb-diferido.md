# ADR-007 — Base vectorial: diferida con criterios objetivos; pgvector como primera ruta

Fecha original: 2026-07-06 · **Revisado: 2026-07-06 (revisión CTO)** · Estado: **Aceptado**
Cambio vs versión anterior: se agrega el problema concreto, las limitaciones reales de
PostgreSQL, comparación ChromaDB/pgvector/Qdrant y gates de migración medibles.

## 1. ¿Qué problema concreto resolvería una base vectorial?

Dos, y solo dos, en este sistema:

- **P1 (MVP):** recuperar correcciones previas *semánticamente* similares para el
  few-shot de clasificación. Ejemplo donde lo léxico falla: "RAPPI RESTAURANTE" y
  "UBER EATS" comparten categoría (delivery) pero cero similitud textual.
- **P2 (Fase 6):** búsqueda semántica sobre transacciones para preguntas en lenguaje
  natural ("¿cuánto gasté en salir a comer?").

## 2. ¿Qué limitaciones tiene PostgreSQL (pg_trgm) para nuestro caso?

- `pg_trgm` mide similitud **léxica**, no semántica: no generaliza entre comercios
  distintos de la misma categoría (el caso P1 de arriba).
- Atenuante decisivo: nuestras descripciones son cortas y formulaicas, y la señal
  dominante es el **nombre del comercio repetido**. Un comercio ya visto se resuelve por
  regla o caché ($0, sin similitud alguna); un comercio nunca visto no tiene vecinos
  útiles ni léxicos ni, con frecuencia, semánticos — y va a revisión manual, que es el
  comportamiento correcto. La ventana donde embeddings agregan valor es real pero estrecha.
- PostgreSQL **no** está limitado a lo léxico: la extensión `pgvector` agrega columnas
  de embeddings e índices HNSW dentro de la misma base. Es decir, "Postgres vs base
  vectorial" es una falsa dicotomía a nuestra escala.

## 3. Comparación de motores

| Criterio | pgvector | ChromaDB | Qdrant |
|---|---|---|---|
| Forma | Extensión de la Postgres existente | Servicio/lib Python aparte | Servidor Rust aparte |
| Piezas nuevas | 0 | +1 almacén (backup y sync propios) | +1 servidor |
| Transaccionalidad con el dominio | Sí (misma transacción, JOIN directo con `classification_decisions`) | No | No |
| Backup | El mismo `pg_dump` de siempre | Separado | Separado |
| Filtros por metadatos | SQL completo | Básicos | Muy buenos |
| Rendimiento a nuestra escala (10³–10⁵ vectores) | Sobrado (HNSW) | Sobrado | Sobrado (irrelevante: todos sobran) |
| Rendimiento a 10⁷+ vectores con filtros ricos | Se degrada | Media | El mejor de los tres |
| Costo operativo | ~0 | Medio | Medio-alto |

Conclusión: a la escala de una vida entera de transacciones personales (~10⁴–10⁵),
la única ventaja de ChromaDB/Qdrant es su API especializada; su costo es una segunda
base de datos que respaldar, sincronizar y mantener consistente con el dominio.
pgvector da el 100% del beneficio con 0 piezas nuevas.

## 4. Decisión

1. MVP: **sin embeddings**. Pipeline reglas → caché de comercio → trigram few-shot → LLM (docs/04).
2. Primera ruta si los datos lo justifican: **pgvector** (Gate 1).
3. Motor dedicado (Qdrant preferido sobre ChromaDB por filtros y madurez operativa):
   solo tras Gate 2. Nota: no verificado el estado actual de cada producto; al llegar a
   Gate 2 se reevalúa con documentación oficial vigente.

## 5. Gates objetivos (evidencia, no opinión)

- **Gate 1 — adoptar pgvector:** requiere (a) ≥1.000 decisiones de usuario acumuladas, y
  (b) evaluación reproducible sobre el dataset dorado (docs/04 §7) donde ocurra una de:
  precision@5 de recuperación trigram < 60% mientras embeddings mejoran ≥15 puntos, **o**
  accuracy de clasificación end-to-end mejora ≥3 puntos con few-shot por embeddings en
  A/B sobre los mismos lotes.
- **Gate 2 — motor dedicado:** solo si pgvector muestra límites operativos medidos:
  p95 de búsqueda >100 ms con índice HNSW bien configurado, o >10⁶ vectores.
  Probabilidad en este proyecto: cercana a cero; se documenta para honestidad del proceso.

## 6. Consecuencias

- (+) La necesidad se demuestra con métricas antes de pagar complejidad.
- (+) El camino de adopción no rompe nada: pgvector es una migración Alembic + un
  retriever alternativo tras la misma interfaz de recuperación de ejemplos.
- (−) Hasta Gate 1, comercios nuevos sin parecido léxico caen a revisión manual: fricción
  aceptada y medida (es parte de la métrica de cobertura, docs/10 §4).
