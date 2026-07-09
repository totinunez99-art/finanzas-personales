# 06 — Seguridad, Privacidad y Backups

> Estado: **Aprobado** · Última actualización: 2026-07-06

## 1. Modelo de amenazas (honesto, no teatral)

Sistema local, mono-usuario, sin exposición a internet. Las amenazas reales son:

| Amenaza | Probabilidad | Mitigación |
|---|---|---|
| Pérdida de datos (disco muere, borrado accidental) | **Alta** — la amenaza #1 real | Backups automáticos y probados (§5) |
| Robo/pérdida del PC | Media | Cifrado de disco (BitLocker) — prerequisito, no opcional |
| Fuga de credenciales (.env en git, en backup) | Media | .gitignore desde commit 1; backups sin .env; App Passwords revocables |
| Exposición accidental de puertos a la red | Baja | Bind a 127.0.0.1 en compose; DB solo en red interna Docker |
| Malware en el PC | Baja-media | Fuera del alcance del proyecto; el cifrado y backups acotan el daño |
| Ataque dirigido remoto | Muy baja | No hay superficie expuesta |

**No** se implementa en MVP: login, RBAC, WAF, rate limiting. Serían teatro de seguridad
para un servicio que solo escucha en localhost. El modelo de permisos multiusuario está
diseñado en el modelo de datos (`user_id` en todo) y se activa en Fase 7.

## 2. Gestión de secretos

- Un solo `.env` (gitignorado) + `.env.example` versionado con todas las claves documentadas.
- Secretos que existirán: App Password de Gmail, API keys de LLM, password de Postgres.
- Regla: ningún secreto en código, logs, mensajes de error ni backups.
- Validación de configuración al arrancar (pydantic-settings): falta una clave → el
  servicio no arranca, con mensaje claro. Nunca defaults silenciosos para secretos.

## 3. Datos en la base

- Cifrado at-rest: delegado al cifrado de disco del SO (BitLocker). Cifrar columnas
  dentro de Postgres agregaría complejidad real (gestión de llaves) contra un atacante
  que, si ya lee los archivos del PC, probablemente también lee la llave. Costo > beneficio aquí.
- `description_raw` es inmutable: es la evidencia auditable de origen de cada dato.

## 4. Privacidad frente a proveedores de IA

- Al LLM viaja **solo**: descripción normalizada, monto, moneda, fecha, taxonomía de
  categorías. Nunca: números de cuenta/tarjeta, saldos, nombre, email, banco.
- Sanitizador previo al prompt que enmascara patrones de PAN (tarjetas), RUT y correos
  si aparecieran incrustados en descripciones. Con test.
- Opción de privacidad máxima soportada desde el día 1: `AI_PROVIDER=ollama` → nada sale del PC.
- Los términos de retención de datos de cada proveedor se documentan en el ADR-004
  cuando se elija el proveedor por defecto (verificar en fuentes oficiales, no asumir).

## 5. Backups (la mitigación más importante del proyecto)

- **Qué:** `pg_dump` (custom format, comprimido) + carpeta de archivos de cartola originales.
- **Cuándo:** job diario del worker (al primer arranque del día) + antes de cada migración de esquema.
- **Dónde:** (1) disco local en carpeta de backups, rotación 30 días; (2) copia cifrada
  (age o 7z AES-256, passphrase fuera del backup) a un destino fuera del PC — la carpeta
  OneDrive del usuario es aceptable **solo cifrado**, jamás el dump plano.
- **Restauración probada:** script `scripts/restore.sh` + prueba de restauración
  automatizada mensual (restaurar a una DB temporal y contar filas). Un backup no
  probado no es un backup; es una esperanza.
- RPO objetivo: 24 h. RTO objetivo: <1 h.

## 6. Logs y observabilidad

> Sección superseded: la estrategia completa vive ahora en [docs/10-observabilidad.md](10-observabilidad.md).
> Se conserva aquí solo lo esencial de logging por su relación con secretos.

- Logging estructurado (JSON) con `structlog`; niveles por módulo vía config.
- Qué se registra: cada batch de importación (métricas por batch), cada llamada LLM
  (proveedor, tokens, costo, latencia, tarea), cada job del scheduler (inicio/fin/error),
  errores con stacktrace. Qué NO: descripciones completas de transacciones en INFO, secretos jamás.
- Destino: stdout → `docker compose logs` + archivo con rotación (7 días). **Sin**
  Prometheus/Grafana/Loki en MVP: para un usuario, una página "Salud del sistema" en el
  dashboard (últimos jobs, errores recientes, correos sin parsear, gasto LLM del mes)
  entrega el 95% del valor con 5% del costo. Se reevalúa si el sistema pasa a un servidor 24/7.

## 7. Revisión crítica

- **Riesgo residual:** el PC no corre 24/7 → si muere el disco un día sin encender,
  se pierde hasta 48 h de datos. Aceptable: los datos fuente (correos, cartolas) siguen
  existiendo en Gmail y el banco; todo es reconstruible por reimportación.
- **Limitación:** backup cifrado a OneDrive depende de disciplina de passphrase
  (guardarla en un gestor de contraseñas, no en el PC).
- **Caso borde:** backup corriendo durante una importación → `pg_dump` es consistente
  por snapshot MVCC; no requiere detener servicios.
- **Deuda aceptada:** sin monitoreo activo de que los backups ocurrieron (el PC apagado
  no puede alertar). Mitigación parcial: la página de salud muestra fecha del último
  backup en rojo si >48 h.
