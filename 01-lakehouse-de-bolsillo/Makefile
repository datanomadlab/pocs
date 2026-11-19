.PHONY: setup demo simular bq test destroy
export PYTHONPATH := src

setup:    ## instala dependencias (requiere uv: https://docs.astral.sh/uv/)
	uv sync

demo:     ## descarga datos, crea la tabla Iceberg, mide DuckDB, simula BigQuery y escribe docs/resultados.md
	uv run python -m lakehouse demo

simular:  ## vuelve a simular BigQuery sin medir de nuevo (necesita make demo antes)
	uv run python -m lakehouse simular
	uv run python -m lakehouse reporte

bq:       ## opcional: mide BigQuery de verdad (GCP_PROYECTO=mi-proyecto make bq)
	uv sync --group bq
	uv run python -m lakehouse bq

test:
	uv run pytest

destroy:  ## borra data/ y, si GCP_PROYECTO está definido, el dataset de BigQuery
	uv run python -m lakehouse destruir
