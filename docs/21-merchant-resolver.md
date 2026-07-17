# 21 — Merchant Resolver: el primer componente con memoria

> Estado: **Implementado (Sprint 3, Bloque 2)** · Creado: 2026-07-09
> Objetivo real: que el Copiloto entienda cada vez mejor los hábitos del usuario.
> Identificar comercios es el medio, no el fin.

## 1. Arquitectura de 5 niveles (requisito del dueño)

| Nivel | Fuente | source | Confianza | Estado |
|---|---|---|---|---|
| 1 | Hint del parser bancario | `hint` | 0.90 (0.98 si una regla lo confirma) | ✅ |
| 2 | Resolver determinista (ruido adquirente TRANSBANK/WEBPAY/MERCADOPAGO/COMPRA \*) | `rule` | 0.85 — SOLO si el candidato ya es un comercio conocido del usuario | ✅ |
| 3 | Base de conocimiento `merchant_rules` (semilla chilena ~22 + crecimiento) | `rule` | seed exact 0.95 / contains 0.90 / promovida 0.96 | ✅ |
| 4 | Corrección del usuario | `user` / regla `origin=user` | 0.99 | ✅ (por grupo, vía teach) |
| 5 | IA | `ai` | por definir | Futuro: entra como un source más, sin migración |

**Regla dura:** `merchant_source='user'` jamás es sobreescrito por ningún nivel
inferior ni futuro (misma filosofía que ADR-008 para categorías).

## 2. El aprendizaje (Nivel 4 → Nivel 3)

`teach(patrón, comercio)`: la corrección del usuario crea una `merchant_rule`
`origin=user, priority=10` (gana a toda semilla) **y se aplica de inmediato** a todas
las transacciones coincidentes. El conocimiento queda disponible para cada importación
futura sin tocar código — el requisito "el conocimiento crece con el uso" es literal:
la UI de la página Comercios muestra los grupos sin resolver ordenados por impacto y
convierte cada respuesta del usuario en regla.

Promoción automática (`origin=promoted`) queda diseñada (columna origin + prioridades)
para cuando exista señal suficiente; no implementada aún (evidencia antes que mecanismo).

## 3. Confidence Explanation

Toda resolución produce `Resolution` con `factors` (nombre + detalle):
coincidencia_regla, hint_coincidente, ensenada_por_usuario, ruido_adquirente,
historial_consistente, sin_conflictos. La explicación completa se persiste en el
evento `merchant.resolved` (payload) y el linaje queda en
`transactions.merchant_rule_id` → reconstruible por SQL. Las confianzas son una
tabla determinista de constantes documentadas, no números mágicos.

## 4. Decisiones de diseño

- **Migración 0004** (revisión previa exigida por el dueño): `merchant_rules` separada
  de `classification_rules` (dominios distintos, misma forma deliberada) + procedencia
  en transactions (source/confidence/rule_id) + backfill de hints existentes.
  Rechazado por anticipación excesiva: tabla maestra de comercios; historial completo
  de resoluciones (valor vigente + linaje + eventos bastan a esta escala).
- **No invención:** ruido adquirente solo resuelve hacia comercios YA conocidos;
  sin evidencia → NULL y el grupo aparece en la página Comercios para que enseñes.
- **ImportService intacto:** la procedencia de hints nuevos se marca en el siguiente
  backfill (deliberado, para no tocar el pipeline; se integrará al pipeline cuando el
  motor de clasificación (B3) defina el paso post-importación único).
- Backfill idempotente (2ª pasada = 0 cambios, 0 eventos — testeado). Bug real cazado
  en desarrollo: la regla se auto-confirmaba como "hint coincidente" en re-ejecuciones.

## 5. Limitaciones honestas

- La explicación viaja en eventos y API pero aún no se MUESTRA por transacción en la
  UI (llega con el detalle de movimiento, bloque 4).
- `known merchants` para el nivel adquirente se recalcula por backfill completo — O(n)
  aceptable a escala personal; optimizable con vista materializada si algún día duele.
- La semilla es juicio chileno-céntrico; el mecanismo teach existe precisamente para
  que la realidad la corrija.
