# Herramientas del repo. Cada experimento tiene además su propio Makefile (setup, demo, test, destroy).
#   make nuevo NN=02               parte un experimento desde _plantilla/
#   make imagenes EXP=02-...       graba la demo y dibuja tablas y diagrama, en ese orden
#   make vocabulario               qué posts de vocabulario faltan
#   make test                      pruebas de tools/
.PHONY: nuevo diagrama tablas demo-gif imagenes vocabulario test exp

# Las imágenes usan cairo. En un Mac donde cairo solo está instalado para x86_64 (/usr/local),
# hay que usar ese Python; si no existe, uv elige uno.
PYTHON_CAIRO := $(shell test -x /usr/local/bin/python3.12 && echo --python /usr/local/bin/python3.12)
MARCA = uv run --no-project $(PYTHON_CAIRO) --with fonttools --with brotli --with cairosvg --with pillow

nuevo:
	@test -n "$(NN)" || (echo "Uso: make nuevo NN=02" && exit 1)
	python3 tools/nuevo.py $(NN)

exp:
	@test -n "$(EXP)" -a -d "$(EXP)" || (echo "Uso: make $(MAKECMDGOALS) EXP=NN-nombre (una carpeta que exista)" && exit 1)

diagrama: exp   ## docs/diagrama.toml -> docs/arquitectura.svg y .png
	$(MARCA) tools/diagrama.py $(EXP)

tablas: exp     ## docs/tablas.toml -> docs/tabla-<id>.png
	$(MARCA) tools/tabla.py $(EXP)

demo-gif: exp   ## docs/demo.toml -> docs/demo.gif. Vuelve a medir: después van las tablas
	$(MARCA) tools/demo.py $(EXP)

# La grabación corre make demo, que vuelve a medir y reescribe docs/tablas.toml y docs/resultados.md.
# Por eso las tablas se dibujan después del GIF: así el GIF, las imágenes y el reporte dicen lo mismo.
imagenes: demo-gif tablas diagrama
	@echo "Revisa que las cifras del README del experimento y de la edición coincidan con $(EXP)/docs/resultados.md"

vocabulario:
	python3 tools/vocabulario.py estado

test:
	uv run --no-project --with pytest --with markdown pytest -q -p no:cacheprovider tools
