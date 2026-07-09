# 05 — Conectores e Integraciones

> Estado: **Aprobado** · Última actualización: 2026-07-06
> Decisión formal: [ADR-003](adr/ADR-003-ingesta-dual.md)

## 1. Diseño del módulo de conectores

Toda fuente de movimientos implementa la misma interfaz (`connectors/base.py`):

```python
class Connector(Protocol):
    name: str                     # "email_imap", "statement_csv_bancochile", ...
    source: SourceType            # email | statement | api
    def fetch(self, ctx: FetchContext) -> list[RawTransaction]: ...

@dataclass(frozen=True)
class RawTransaction:             # contrato único de salida de TODO conector
    account_hint: str             # cómo el conector identifica la cuenta
    posted_at: date
    amount: Decimal               # negativo=cargo
    currency: str
    description_raw: str
    source: SourceType
    source_ref: str               # msg-id / archivo+fila
    occurred_at: datetime | None = None
    merchant_hint: str | None = None
    installment_raw: str | None = None   # "03/12" si aparece en el texto
```

`ImportService` consume `RawTransaction[]` sin saber de dónde vienen. Agregar un banco
o una futura API bancaria = escribir un conector nuevo; **cero cambios** en core.
Esto cumple el requisito de "puerta abierta a API bancaria sin rediseño".

## 2. Conector email (señal temprana, provisoria)

- **Protocolo:** IMAP solo-lectura sobre Gmail, con **App Password dedicada** y, mejor,
  una etiqueta/filtro de Gmail que agrupe solo correos bancarios (el sistema lee esa
  etiqueta, no todo el buzón — minimización de acceso).
- **Polling:** al iniciar el PC y cada 15 min (APScheduler). Estado incremental por
  `UID` de IMAP (no se reprocesa lo ya visto). *No es tiempo real y no se promete tiempo real.*
- **Parsing:** una plantilla por (banco, tipo de correo): compra TC, transferencia
  recibida/enviada, cargo, giro. Plantillas = regex + selectores sobre HTML, versionadas
  y con fixture de test cada una.
- **Correo que no matchea ninguna plantilla:** se guarda su referencia en cola
  `unparsed_emails` visible en dashboard. NUNCA se descarta en silencio — un formato
  nuevo de correo es información, no ruido.
- Toda transacción de email nace `provisional` (ciclo de vida en docs/03 §5).

## 3. Conector cartolas (fuente de verdad)

- Un parser por (banco, formato). Prioridad de formato: **XLSX/CSV > PDF** (PDF solo si
  el banco no ofrece otra cosa; parseo con pdfplumber, tolerancia cero a ambigüedad:
  ante duda, el batch falla con error claro en vez de insertar datos dudosos).
- Detección automática de banco/formato por estructura del archivo, con confirmación
  del usuario en la primera importación de cada tipo.
- Validaciones por batch: continuidad de fechas con el período declarado, cuadratura
  saldo inicial + suma de movimientos = saldo final (cuando la cartola trae saldos).
  Si no cuadra → batch en estado `warning`, visible, nunca silencioso.
- Idempotencia: `sha256` de archivo único por cuenta (docs/03) + dedup por transacción.

## 4. Integraciones externas del MVP

| Integración | Uso | Modo | Riesgo |
|---|---|---|---|
| Gmail IMAP | correos bancarios | lectura, App Password | revocable en 1 clic; contraseña en `.env` local |
| mindicador.cl | UF/USD diarios | HTTP público | API gratuita sin SLA; fallback: última tasa conocida + fuente alternativa (api.sbif/CMF) documentada |
| LLM (Claude/OpenAI/Gemini/Ollama) | clasificación | vía capa `ai/` | ver docs/04 y docs/06 §4 |

## 5. Futuro (documentado, no construido)

- **API bancaria (Fintoc u otro):** entra como un `Connector` más. Criterio de adopción:
  cuando el costo mensual < valor del tiempo ahorrado en descargas manuales, y tras
  evaluar el riesgo de entregar credenciales a un agregador. No antes de Fase 3.
- **Scraping bancario: descartado.** Frágil, potencial violación de términos de servicio
  del banco, y riesgo de bloqueo de cuenta. Se reevalúa solo si un banco no ofrece ni
  cartola descargable ni correos útiles.

## 6. Revisión crítica

- **Riesgo mayor del sistema completo:** los bancos cambian plantillas de correo y
  formato de cartola sin aviso. Mitigaciones: (a) cola de no-parseados visible,
  (b) métrica "correos parseados/recibidos" en dashboard con alerta de degradación,
  (c) fixtures de regresión por banco, (d) la cartola como red de seguridad — si el
  email falla un mes entero, la cartola reconstruye todo.
- **Caso borde:** compras en USD con TC chilena (facturación dual). El correo suele
  informar USD y la cartola CLP → el matching por monto exacto falla. Regla adicional:
  match por comercio+fecha con conversión aproximada vía `exchange_rates` ±2%.
- **Caso borde:** cartolas de tarjeta de crédito ≠ cartolas de cuenta corriente
  (facturado vs no facturado). El parser de TC debe distinguir movimientos del período
  vs cuotas futuras; en MVP las cuotas futuras se capturan en `installment_raw` y se
  ignoran en reportes (Fase 2 las estructura).
- **No verificado:** bancos concretos de Tomás y sus formatos. Primer paso de la
  implementación: recolectar 2-3 meses de cartolas y correos reales, anonimizarlos y
  convertirlos en fixtures antes de escribir el primer parser.
