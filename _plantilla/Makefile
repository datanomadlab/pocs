.PHONY: setup demo test destroy
export PYTHONPATH := src

setup:    ## instala dependencias (requiere uv: https://docs.astral.sh/uv/)
	uv sync

demo:     ## descarga los datos, corre el experimento, escribe docs/resultados.md y muestra el resumen
	uv run python -m {{paquete}} demo

test:
	uv run pytest

destroy:  ## borra data/ y todo lo que el experimento haya creado en la nube
	uv run python -m {{paquete}} destruir
