# 15 — Instalación y Resolución de Problemas

> Estado: **Vivo** · Creado: 2026-07-06 (cierre Sprint 1)
> Objetivo: clonar → flujo completo funcionando con datos ficticios en <10 minutos.

## 1. Requisitos

- Docker Desktop (con WSL2 en Windows) corriendo.
- Git.
- (Solo para Demo Mode por consola y desarrollo) Python 3.12+.

## 2. Instalación con Docker (camino recomendado) — un solo comando

```bash
git clone <url-del-repo> finanzas-personales
cd finanzas-personales
copy .env.example .env          # Windows (Linux/macOS: cp)
# Editar .env: definir POSTGRES_PASSWORD y ajustar DATABASE_URL con ese password
docker compose up --build
```

**No se requiere ningún comando adicional.** Flujo de arranque garantizado por compose:

```
db (healthcheck pg_isready) ──sana──▶ bootstrap (one-shot):
                                        1. espera conexión real a PG (reintentos 60s)
                                        2. alembic upgrade head   (idempotente)
                                        3. usuario por defecto    (idempotente)
                                      ──éxito──▶ api + worker ──▶ dashboard
```

Si `bootstrap` falla, api y worker NO arrancan (jamás tocan tablas inexistentes) y
`docker compose logs bootstrap` muestra la causa en un mensaje accionable.

Verificación en el navegador:
- http://localhost:8000/health → `{"status":"ok", "db":true, "migration":"0002", ...}`
- http://localhost:8501 → dashboard con métricas en verde.

## 3. Demo Mode (datos 100% ficticios, opt-in)

```bash
docker compose run --rm demo
```
Es deliberadamente manual: cargar datos ficticios automáticamente contaminaría un
sistema con datos reales.
Crea "Cuenta Demo (datos ficticios)" e importa dos meses ficticios, demostrando el
dedup (julio trae una fila repetida de junio → "1 duplicado omitido"). Luego, prueba
manual del wizard completo: en el dashboard → **Importar**, arrastrar
`scripts/demo_data/demo_agosto_para_wizard.csv`, revisar la vista previa y confirmar.

El script es idempotente: correrlo de nuevo reporta "ya estaba importado".

## 4. Desarrollo local sin Docker (solo la DB en contenedor)

```bash
docker compose up -d db
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/bootstrap.py                      # espera DB + migra + usuario (todo en uno)
uvicorn finanzas.api.main:app --reload           # terminal 1
streamlit run src/finanzas/dashboard/app.py      # terminal 2 (API_BASE_URL=http://localhost:8000)
```

## 5. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `relation "job_runs" does not exist` (o cualquier tabla) | Un servicio tocó la DB antes de las migraciones — **resuelto estructuralmente** con el servicio `bootstrap`; si reaparece, algo saltó el orden | `docker compose logs bootstrap`; verificar que api/worker tengan `depends_on: bootstrap: service_completed_successfully` |
| `bootstrap` termina con error | Password inconsistente, DB inaccesible o migración fallida | `docker compose logs bootstrap` — el mensaje indica la causa exacta |
| api/worker no arrancan y compose queda esperando | `bootstrap` falló (los servicios dependen de su éxito) | Corregir la causa del bootstrap y `docker compose up` de nuevo |
| `POSTGRES_PASSWORD: definir en .env` al levantar compose | `.env` no existe o sin password | `copy .env.example .env` y completar |
| API arranca pero `/health` da `db: false` o error de conexión | `DATABASE_URL` en `.env` con password distinto al de `POSTGRES_PASSWORD` | Ambos valores deben coincidir |
| Cambié `POSTGRES_DB`/`POSTGRES_USER` en `.env` y la DB no existe | El contenedor postgres solo crea la DB en el PRIMER arranque del volumen | `docker compose down -v` (⚠ borra datos) o crear la DB a mano |
| `503: No existe el usuario por defecto` en el dashboard | Bootstrap no corrió tras un reset de datos | `docker compose up` (bootstrap lo recrea) o `docker compose run --rm bootstrap` |
| `port is already allocated` (5432/8000/8501) | Otro servicio usa el puerto | Detener el otro servicio o cambiar el puerto izquierdo en compose |
| Dashboard: "Sin conexión con la API" | contenedor `api` caído o aún migrando | `docker compose logs api`; esperar `Application startup complete` |
| Importación responde 409 | El MISMO archivo ya fue importado en esa cuenta | Es el comportamiento correcto (idempotencia); usa un archivo nuevo |
| Importación responde 415 "formato aún no compatible" | El archivo no coincide con ningún parser | Esperado para cartolas bancarias reales hoy; ver docs/14 §4 para el formato puente y §5 para crear el parser del banco |
| Error 422 con "Fila N" | Contenido inválido en esa fila del CSV | Corregir la fila indicada; el sistema no adivina (tolerancia cero) |
| Compose muy lento o errores raros de archivos en Windows | Repo dentro de OneDrive: la sincronización pelea con Docker/venv | Clonar a una ruta NO sincronizada (ej. `C:\dev\finanzas-personales`) para EJECUTAR; OneDrive/GitHub siguen siendo el respaldo del código |
| CI roja en el primer push | Este código aún no se había ejecutado (ver MASTER_PROJECT §1) | Leer el log del job que falló; los ajustes esperables son menores (imports, tipos) |
| `alembic` falla con "relation already exists" | DB con estado a medias de una prueba anterior | `docker compose down -v` (⚠ borra datos) y volver a levantar |

## 6. Reinicio limpio total

```bash
docker compose down -v      # ⚠ elimina la base de datos completa
docker compose up --build   # bootstrap re-migra y re-crea el usuario solo
docker compose run --rm demo   # opcional: repoblar datos ficticios
```

## 7. Dónde mirar cuando algo falla

1. `docker compose logs api --tail 100` — errores de API y migraciones.
2. `docker compose logs worker --tail 50` — jobs.
3. Dashboard (página principal) — semáforo de salud, últimos jobs.
4. Si el error no está en la tabla §5: abrir issue con el log y agregar el caso a esta tabla al resolverlo.
