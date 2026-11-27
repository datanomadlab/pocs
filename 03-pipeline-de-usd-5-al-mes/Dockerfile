# La imagen del job: la misma corre en local con make demo y en Cloud Run.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache && rm /usr/local/bin/uv
COPY src/ src/
COPY sql/ sql/
# En Cloud Run solo se puede escribir en memoria: todo lo temporal va a /tmp.
ENV PATH=/app/.venv/bin:$PATH PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HOME=/tmp DLT_DATA_DIR=/tmp/dlt RUNTIME__DLTHUB_TELEMETRY=false
CMD ["python", "-m", "pipeline.job_dlt"]
