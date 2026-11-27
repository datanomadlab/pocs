.PHONY: setup demo reporte test destroy
export PYTHONPATH := src
export PYTHONUNBUFFERED := 1

setup:    ## instala dependencias (requiere uv y Docker) y baja la imagen de Postgres
	uv sync
	docker pull -q $${IMAGEN_POSTGRES:-postgres:18.7}

demo:     ## descarga los datos, simula 30 días, corre las 7 pruebas, escribe docs/resultados.md y muestra el resumen
	uv run python -m pipeline demo

reporte:  ## vuelve a escribir el reporte y los costos desde la última medición, sin medir de nuevo
	uv run python -m pipeline reporte

test:
	uv run pytest

destroy:  ## borra los contenedores, la imagen del job y data/. En la nube no se crea nada
	uv run python -m pipeline destruir
