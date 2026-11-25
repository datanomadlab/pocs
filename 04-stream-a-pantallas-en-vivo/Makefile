.PHONY: setup demo costos local concurrencia test destroy
export PYTHONPATH := src
export PYTHONUNBUFFERED := 1
# Lo que cambies en .env (ver .env.example) llega al experimento.
-include .env
export

setup:    ## instala dependencias (requiere uv y Docker: https://docs.astral.sh/uv/)
	uv sync

demo:     ## construye las imágenes, mide cada ruta, calcula costos, escribe docs/resultados.md y muestra el resumen
	uv run python -m stream demo

costos:   ## recalcula solo el modelo de costos sobre la última medición (por ejemplo, tras cambiar escenario.toml)
	uv run python -m stream costos
	uv run python -m stream reporte

local:    ## el modelo de costos con tus cifras (escenario.local.toml). Sale a la terminal y a data/; no se sube
	uv run python -m stream local

concurrencia:  ## miles de pantallas, varias por cuenta: carga, rampa y corte. Cerca de una hora; sale a la terminal y a data/
	uv run python -m stream concurrencia

test:
	uv run pytest

destroy:  ## baja los contenedores y borra volúmenes, imágenes propias y data/. Nada corre en la nube
	uv run python -m stream destruir
