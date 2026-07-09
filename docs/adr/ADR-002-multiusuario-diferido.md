# ADR-002 — Multiusuario: modelado hoy, implementado nunca-hasta-que-haga-falta

Fecha: 2026-07-06 · Estado: **Aceptado**

## Contexto
Requisito del dueño: "no rediseñar la arquitectura en dos años si esto se vuelve SaaS".
Riesgo opuesto: construir auth, tenancy y billing para un usuario es sobre-ingeniería
clásica que retrasa el valor real.

## Alternativas
1. Multi-tenancy completo hoy (auth, RBAC, aislamiento): semanas de trabajo sin usuario que lo necesite.
2. Ignorar el futuro (sin `user_id`): migrar después toca cada tabla, cada query y cada test. Caro.
3. **Seguro barato (elegida):** pagar solo lo que es caro de retrofit y barato de hacer ahora.

## Decisión
Se implementa hoy, porque retrofitearlo es caro:
- `user_id` en toda tabla de datos de usuario; queries siempre filtradas por usuario
  (vía repositorio base, no por disciplina manual).
- Ningún código asume "el" usuario: el usuario actual llega por contexto/dependencia.
- Secretos y config por variables de entorno (no rutas hardcodeadas).

Se difiere explícitamente a Fase 7: login/auth, RBAC, aislamiento fuerte (RLS de
Postgres), billing, onboarding, multi-tenancy de conectores.

## Consecuencias
- (+) La migración a SaaS es agregar capas, no reescribir el modelo de datos.
- (−) Levísima fricción diaria (pasar `user_id` por las capas).
- (−) Honestidad: un SaaS real igualmente exigirá trabajo grande (auth, RLS, infra).
  Este ADR evita el **rediseño del dominio**, no todo el trabajo.
