# ADR-001 — Monolito modular en vez de microservicios

Fecha: 2026-07-06 · Estado: **Aceptado**

## Contexto
Sistema mono-usuario en un PC local, con visión de posible SaaS futuro. Tentación:
"diseñar para escalar" con servicios separados.

## Alternativas
1. **Monolito modular** (elegida): un backend FastAPI con módulos de frontera estricta
   (core/connectors/ai/api/workers) comunicados por interfaces.
2. Microservicios: aislamiento real, pero N contenedores, contratos de red, versionado
   entre servicios y debugging distribuido — para un solo usuario. Costo enorme, beneficio nulo hoy.
3. Script monolítico sin fronteras: rápido hoy, invendible en 6 meses; cada cambio toca todo.

## Decisión
Monolito modular. La escalabilidad futura se protege con **fronteras de módulo**, no con
procesos separados: si un módulo debe extraerse a servicio (ej. workers a un VPS), la
interfaz ya existe y la extracción es mecánica.

## Consecuencias
- (+) Un solo deploy, debugging simple, refactors baratos.
- (−) Exige disciplina: la frontera la protege la revisión de código y un lint de
  imports (`import-linter` con contrato de capas), no el runtime.
- Revisión: si aparece un segundo usuario real o un servidor 24/7, reevaluar separación de workers.
