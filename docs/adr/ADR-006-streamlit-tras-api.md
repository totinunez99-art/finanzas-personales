# ADR-006 — Streamlit como dashboard MVP, siempre detrás de la API

Fecha: 2026-07-06 · Estado: **Aceptado**

## Contexto
Se necesita UI para: dashboard, cola de revisión de clasificaciones, carga de cartolas,
página de salud. El stack preferido propone Streamlit.

## Alternativas
1. **Streamlit (elegida para MVP):** velocidad de desarrollo imbatible para UI de datos;
   Python puro. Contras: estado/interactividad limitados, no apto para SaaS multiusuario.
2. Frontend real (React/Next): apto para el futuro SaaS pero semanas de trabajo extra
   ahora, en el momento de mayor incertidumbre sobre qué pantallas importan.
3. Jinja + HTMX sobre FastAPI: intermedio interesante, más trabajo que Streamlit y menos
   estándar que React. Descartado por no ser óptimo en ningún horizonte.

## Decisión
Streamlit, con una regla no negociable: **habla solo con la API HTTP, jamás con la DB**.
Streamlit es descartable por diseño; la lógica vive toda detrás de la API. El día que se
reemplace (Fase 6-7), se reescribe solo presentación.

## Consecuencias
- (+) Pantallas útiles en días; iteración rápida sobre qué información importa de verdad.
- (−) Doble trabajo aparente (endpoint + pantalla). Es deliberado: los endpoints son el
  producto de largo plazo; las pantallas Streamlit son andamio.
- (−) La cola de revisión exige interactividad fina (aprobar/corregir rápido); si
  Streamlit la hace tortuosa, ese será el primer candidato a HTMX/React. Métrica: si
  corregir una transacción toma >2 clics o >2 s, la UI está fallando su objetivo.
