#!/usr/bin/env python3
"""Dibuja el diagrama de un experimento con el estilo de la marca (1600x900, SVG + PNG).

Uso, desde la raíz del repo:
    uv run --no-project --with fonttools --with brotli --with cairosvg --with pillow \
        tools/diagrama.py 01-lakehouse-de-bolsillo          # diagrama de un experimento
    ... tools/diagrama.py vocabulario/imagenes/docker.toml  # imagen de un post de vocabulario

Con una carpeta de experimento lee docs/diagrama.toml y escribe arquitectura.svg y arquitectura.png
al lado. Con un archivo .toml escribe un .png con el mismo nombre (sin .svg, para no engordar el repo).
Las fuentes y las funciones de dibujo vienen del repo del sitio (brand/_build/generar_assets.py).
Si no está en ../datanomadlab, indica la ruta con la variable DNL_SITIO.
Necesita la librería cairo de la misma arquitectura que el Python que uses (brew install cairo).
"""
from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

ANCHO, ALTO = 1600, 900


def cargar_marca():
    sitio = Path(os.environ.get("DNL_SITIO", Path(__file__).resolve().parents[2] / "datanomadlab"))
    generador = sitio / "brand" / "_build"
    if not (generador / "generar_assets.py").exists():
        sys.exit(f"No encuentro el generador de marca en {generador}. Define DNL_SITIO.")
    sys.path.insert(0, str(generador))
    import generar_assets
    return generar_assets


def dibujar(spec: dict, m) -> str:
    def caja(c: dict) -> str:
        borde = m.AMBER if c.get("veredicto") or c.get("resultado") else m.DEEP
        x, y, w, h = c["x"], c["y"], c["w"], c["h"]
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{m.PAPER}" '
                f'stroke="{borde}" stroke-width="3"/>'
                + m.text(m.MONO, c["titulo"], 24, x + 24, y + 46, m.INK)
                + m.text(m.SANS, c["detalle"], 19, x + 24, y + 80, m.MUTED))

    cuerpo = m.isotipo(72, 56, 44)
    cuerpo += m.text(m.DISPLAY_XB, "datanomadlab", 30, 130, 88, m.INK, m.TRACK_DISPLAY)
    etiqueta = spec.get("etiqueta") or f"Experimento {spec['numero']}"
    cuerpo += m.text(m.MONO, etiqueta, 24, ANCHO - 72, 88, m.DEEP, 0, "end")
    cuerpo += m.text(m.DISPLAY_XB, spec["titulo"], 56, 72, 190, m.INK, m.TRACK_DISPLAY)
    cuerpo += m.text(m.SANS, spec["pregunta"], 24, 72, 236, m.MUTED)
    trazo = f'fill="none" stroke="{m.DEEP}" stroke-width="3" stroke-linejoin="round"'
    cuerpo += "".join(f'<path d="{d}" {trazo}/>' for d in spec["conectores"])
    cuerpo += "".join(caja(c) for c in spec["caja"])
    if spec.get("nota"):
        cuerpo += m.text(m.SANS, spec["nota"], 19, 72, 800, m.MUTED)
    return m.svg(ANCHO, ALTO, cuerpo, m.PAPER)


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    origen = Path(sys.argv[1])
    suelto = origen.suffix == ".toml"
    definicion = origen if suelto else origen / "docs" / "diagrama.toml"
    if not definicion.exists():
        sys.exit(f"No existe {definicion}")
    with definicion.open("rb") as f:
        spec = tomllib.load(f)
    m = cargar_marca()
    svg = dibujar(spec, m)
    png = definicion.with_suffix(".png") if suelto else definicion.with_name("arquitectura.png")
    if not suelto:
        definicion.with_name("arquitectura.svg").write_text(svg, encoding="utf-8")
    m.cairosvg.svg2png(bytestring=svg.encode(), write_to=str(png))
    print(f"Listo: {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
