# 01 — Visión, Objetivos y Roadmap

> Estado: **Aprobado** · Última actualización: 2026-07-06 · Dueño: Tomás

## 1. Visión

Copiloto Financiero Personal basado en IA. No un registro de gastos: un sistema que
comprende las finanzas del usuario y ayuda a tomar mejores decisiones.

Comienza como herramienta personal (un usuario, PC local). Las decisiones de diseño
no deben **bloquear** una evolución futura a SaaS multiusuario, pero tampoco se
construye infraestructura multiusuario hoy (ver [ADR-002](adr/ADR-002-multiusuario-diferido.md)).

**Principio rector:** el sistema vale solo si Tomás lo usa a diario. Cada decisión se
evalúa primero contra fricción de uso, después contra elegancia técnica.

## 2. Contexto

- País: Chile. Monedas: CLP (principal), UF, USD.
- Despliegue: PC personal con Docker (no 24/7). Implicancia: los procesos automáticos
  operan por *polling* al estar el PC encendido; no existe "tiempo real" (ver docs/05).
- Costo objetivo: US$0/mes de infraestructura. Único costo variable: tokens de LLM
  (mitigable con modelos locales vía Ollama).

## 3. Objetivos funcionales

### MVP (Fase 1) — criterio de éxito: uso diario real durante 4 semanas seguidas

1. Importar movimientos desde correos bancarios (IMAP, polling).
2. Importar cartolas CSV/Excel/PDF como fuente oficial.
3. Normalizar, deduplicar y reconciliar transacciones (email ↔ cartola).
4. Clasificar transacciones con IA (categoría + comercio + confianza).
5. Corrección manual con mínima fricción (cola de revisión en dashboard).
6. Aprender de correcciones (reglas + few-shot; ver docs/04).
7. Dashboard Streamlit: saldo por cuenta, gastos por categoría, evolución mensual,
   movimientos recientes, cola de pendientes de revisión.

### Fases posteriores (documentadas, NO construidas)

| Fase | Alcance | Prerrequisito |
|---|---|---|
| 2 | Suscripciones y pagos recurrentes; detección de duplicados avanzada; cuotas de tarjeta | ≥3 meses de datos limpios |
| 3 | Deudas, línea de crédito, indicadores financieros (tasa de ahorro, burn rate) | Fase 2 estable |
| 4 | Inversiones, patrimonio neto, multi-moneda avanzada (UF/USD históricos) | Fase 3 |
| 5 | Proyección de flujo de caja, detección de anomalías, reportes automáticos | Fase 4 + historial ≥6 meses |
| 6 | Preguntas en lenguaje natural, recomendaciones de acción | Fase 5 |
| 7 | (Condicional) SaaS multiusuario: auth real, aislamiento, billing | Decisión de negocio explícita |

**Regla anti-scope-creep:** ninguna funcionalidad de fase N+1 entra mientras la fase N
no cumpla su criterio de salida (definido al iniciar cada fase en MASTER_PROJECT.md).

## 4. Objetivos no funcionales

| Atributo | Objetivo concreto (verificable) |
|---|---|
| Confiabilidad de datos | 0 transacciones duplicadas tras reconciliación; toda importación es idempotente y re-ejecutable |
| Fricción de uso | Importar una cartola: ≤2 minutos. Corregir una clasificación: ≤2 clics |
| Privacidad | Datos financieros nunca salen del PC, salvo texto mínimo enviado al LLM (ver docs/06 §4) |
| Mantenibilidad | Un módulo nuevo de conector o proveedor IA no toca código existente (interfaces estables) |
| Portabilidad | `docker compose up` levanta todo; backup restaurable probado |
| Costo | US$0 infraestructura; presupuesto LLM ≤ US$5/mes con alerta |
| Observabilidad | Toda importación y clasificación deja rastro auditable (qué, cuándo, fuente, resultado) |

## 5. No-objetivos (explícitos)

- No es una app móvil.
- No ejecuta pagos ni mueve dinero. Solo lee, analiza y recomienda.
- No reemplaza asesoría financiera profesional.
- No soporta múltiples usuarios en el MVP (el modelo de datos lo permite; el software no lo implementa).

## 6. Riesgo existencial del proyecto

El riesgo #1 no es técnico: es **abandono por fricción**. Sistemas de finanzas
personales mueren cuando importar/corregir datos cuesta más que el valor percibido.
Por eso el MVP optimiza el ciclo importar→clasificar→corregir→confiar, y nada más.
Ver registro completo en docs/09-riesgos.md.
