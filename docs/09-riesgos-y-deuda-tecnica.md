# 09 — Registro de Riesgos y Deuda Técnica

> Estado: **Vivo** — se actualiza en cada fase · Última actualización: 2026-07-06
> Escala: Impacto × Probabilidad (A=alto, M=medio, B=bajo)

## 1. Riesgos abiertos

| ID | Riesgo | I×P | Mitigación | Estado |
|---|---|---|---|---|
| R-01 | **Abandono por fricción**: el usuario deja de importar/corregir y el sistema muere | A×A | MVP obsesionado con el ciclo diario; criterio de éxito = 4 semanas de uso real; medir fricción (tiempo de corrección) | Abierto — riesgo #1 |
| R-02 | Bancos cambian plantillas de correo/cartola sin aviso | A×A | Cola de no-parseados visible, métrica de degradación, fixtures de regresión, cartola como red de seguridad | Abierto — permanente |
| R-03 | Pérdida de datos (disco, borrado) | A×M | Backups diarios + copia cifrada externa + restauración probada mensual (docs/06 §5) | Abierto |
| R-04 | Reconciliación email↔cartola produce duplicados o pierde movimientos | A×M | Constraint de unicidad en DB, matching conservador (ambigüedad→revisión), reportes separan provisorio | Abierto |
| R-05 | Parseo PDF impreciso inserta datos erróneos | A×M | Preferir CSV/XLSX; PDF con cuadratura de saldos y fallo explícito ante ambigüedad | Abierto |
| R-06 | Clasificación IA mal calibrada genera datos falsos "confiables" | M×M | Modo sombra 2 semanas, umbral calibrado con datos, evaluación semanal contra dataset dorado | Abierto |
| R-07 | Costo LLM se descontrola | B×B | Pipeline reglas-primero, batch, presupuesto con alerta, opción Ollama | Abierto |
| R-08 | mindicador.cl desaparece o falla | M×B | Fallback última tasa conocida; fuente alternativa (CMF) documentada | Abierto |
| R-09 | Secretos filtrados (git, backup, prompt) | A×B | .gitignore día 1, backups sin .env, sanitizador de prompts con test | Abierto |
| R-10 | Scope creep: construir fases futuras antes de que el MVP se use | M×A | Regla anti-scope-creep (docs/01 §3); MASTER_PROJECT.md como control | Abierto |
| R-11 | Gmail deshabilita App Passwords o cambia política IMAP | M×B | Alternativa documentada: OAuth2 para IMAP (más setup, mismo conector) | Abierto |

## 2. Deuda técnica aceptada deliberadamente (con fecha de revisión)

| ID | Deuda | Por qué se acepta | Se paga cuando |
|---|---|---|---|
| D-01 | Sin auth/login | Sistema local mono-usuario en localhost | Fase 7 o exposición a red |
| D-02 | `installment_info` como jsonb laxo | Cuotas no son alcance MVP; capturar el dato crudo es barato | Fase 2 (tabla `installment_plans`) |
| D-03 | Sin colas/eventos; jobs secuenciales | Escala no lo exige | Si un job bloquea >5 min de forma recurrente |
| D-04 | Sin Prometheus/Grafana; observabilidad = página de salud + logs | Un usuario, un PC | Servidor 24/7 o multiusuario |
| D-05 | Migraciones Alembic al arrancar la API | Seguro mono-instancia | Fase 7 (pipeline de deploy) |
| D-06 | Detección de transferencias entre cuentas propias: manual (categoría `transfer`) | Automatizarla requiere heurísticas con datos reales | Fase 2 |
| D-07 | mypy estricto solo en core/shared | Velocidad de arranque | Expandir módulo a módulo |

## 3. Problemas conocidos

(Ninguno aún — no hay código. Esta sección se llena durante la implementación y se
replica el estado en MASTER_PROJECT.md.)
