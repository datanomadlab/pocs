.PHONY: setup demo bq test destroy
export PYTHONPATH := src

setup:    ## instala dependencias (requiere uv: https://docs.astral.sh/uv/)
	uv sync

demo:     ## descarga datos, crea la tabla Iceberg, mide DuckDB y escribe docs/resultados.md
	uv run python -m lakehouse demo

bq:       ## opcional: mide BigQuery de verdad (GCP_PROYECTO=mi-proyecto make bq)
	uv sync --group bq
	uv run python -m lakehouse bq

test:
	uv run pytest

destroy:  ## borra data/ y, si GCP_PROYECTO está definido, el dataset de BigQuery
	uv run python -m lakehouse destruir
