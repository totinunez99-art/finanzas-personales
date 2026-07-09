# ADR-003 — Ingesta dual: email como señal temprana, cartola como fuente de verdad

Fecha: 2026-07-06 · Estado: **Aceptado**

## Contexto
Chile, sin open banking gratuito. Opciones: cartolas manuales, correos de notificación,
API agregador (Fintoc, pago), scraping.

## Alternativas
1. Solo cartolas: robusto y gratis, pero datos con días/semanas de rezago y fricción mensual.
2. Solo email: casi inmediato pero incompleto (no todo movimiento genera correo) y frágil
   (plantillas cambian). Inaceptable como única fuente: produce una base incompleta en silencio.
3. API agregador: automática pero con costo mensual y entrega de credenciales bancarias a un tercero.
4. Scraping: **descartado** — frágil y con riesgo de violar términos del banco.
5. **Dual email+cartola (elegida)** tras un módulo de conectores con interfaz común.

## Decisión
Email produce transacciones `provisional`; la cartola confirma vía reconciliación
(docs/03 §5). Los reportes distinguen confirmado de provisorio. La interfaz `Connector`
permite sumar una API agregadora después sin tocar el core.

## Consecuencias
- (+) Costo $0, latencia de horas para gastos con correo, base final siempre completa vía cartola.
- (−) La reconciliación es el componente más complejo del MVP; se paga con tests exhaustivos.
- (−) Mantenimiento perpetuo de parsers. Mitigado con fixtures de regresión y cola de no-parseados.
- Revisión: adoptar API agregadora cuando su costo < valor del tiempo de descarga manual (evaluar en Fase 3).
