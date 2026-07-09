FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Capa de dependencias (se cachea mientras pyproject no cambie)
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts

# Comando definido por servicio en docker-compose.yml
CMD ["uvicorn", "finanzas.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
