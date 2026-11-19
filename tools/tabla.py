#!/usr/bin/env python3
"""Dibuja las tablas de un experimento como imágenes con el estilo de la marca (1600 de ancho, PNG).

Substack no tiene tablas, así que el post las lleva como imagen. Uso, desde la raíz del repo:
    uv run --no-project --with fonttools --with brotli --with cairosvg --with pillow \
        tools/tabla.py 01-lakehouse-de-bolsillo

Lee docs/tablas.toml (lo escribe `make demo`) y escribe docs/tabla-<id>.png por cada tabla.
Las fuentes y colores vienen del repo del sitio, igual que tools/diagrama.py.
Cada columna lleva su etiqueta (medido, estimado, simulado, modelo) con un color fijo.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from diagrama import cargar_marca

ANCHO = 1600
MARGEN = 72
FILA = 66
TAM = 23
SEPARACION_COLUMNAS = 48


def color_etiqueta(m, etiqueta: str) -> str:
    return {"medido": m.MINT_DARK, "estimado": m.AMBER, "simulado": m.DEEP}.get(etiqueta, m.MUTED)


def anchos(m, t: dict) -> list[float]:
    """La primera columna toma lo que necesita; el resto se reparte en partes iguales."""
    filas = t["filas"] + ([t["total"]] if t.get("total") else [])
    primera = max(m.SANS.width(f[0], TAM) for f in filas) + SEPARACION_COLUMNAS
    resto = (ANCHO - 2 * MARGEN - primera) / (len(t["columnas"]) - 1)
    necesario = max(max(m.SANS_MED.width(c, TAM), m.MONO.width(str(v), TAM))
                    for i, c in enumerate(t["columnas"][1:], 1) for v in [f[i] for f in filas])
    if necesario + SEPARACION_COLUMNAS > resto:
        raise ValueError(f"la tabla '{t['id']}' no cabe en {ANCHO} px: acorta los textos")
    return [primera] + [resto] * (len(t["columnas"]) - 1)


def dibujar(t: dict, numero: str, m) -> tuple[str, int]:
    cuerpo = m.isotipo(MARGEN, 56, 44)
    cuerpo += m.text(m.DISPLAY_XB, "datanomadlab", 30, 130, 88, m.INK, m.TRACK_DISPLAY)
    cuerpo += m.text(m.MONO, f"Experimento {numero}", 24, ANCHO - MARGEN, 88, m.DEEP, 0, "end")
    cuerpo += m.text(m.DISPLAY_XB, t["titulo"], 48, MARGEN, 180, m.INK, m.TRACK_DISPLAY)
    w = anchos(m, t)
    bordes = [MARGEN + sum(w[:i + 1]) for i in range(len(w))]   # borde derecho de cada columna

    def fila(valores: list[str], y: float, cara, color: str) -> str:
        s = m.text(cara, valores[0], TAM, MARGEN, y, color)
        return s + "".join(m.text(m.MONO if cara is not m.SANS_MED else cara, str(v), TAM, bordes[i], y,
                                  color, 0, "end") for i, v in enumerate(valores[1:], 1))

    y = 262
    cuerpo += fila(t["columnas"], y, m.SANS_MED, m.INK)
    cuerpo += "".join(m.text(m.MONO, e, 17, bordes[i], y + 30, color_etiqueta(m, e), 0, "end")
                      for i, e in enumerate(t["etiquetas"]) if e)
    y += 56
    cuerpo += f'<rect x="{MARGEN}" y="{y}" width="{ANCHO - 2 * MARGEN}" height="3" fill="{m.DEEP}"/>'
    for valores in t["filas"]:
        y += FILA
        cuerpo += fila(valores, y - 24, m.SANS, m.INK)
        cuerpo += f'<rect x="{MARGEN}" y="{y}" width="{ANCHO - 2 * MARGEN}" height="1.5" fill="{m.LINE}"/>'
    if t.get("total"):
        y += FILA
        cuerpo += f'<rect x="{MARGEN}" y="{y - FILA}" width="{ANCHO - 2 * MARGEN}" height="{FILA}" fill="{m.MIST}"/>'
        cuerpo += fila(t["total"], y - 24, m.SANS_MED, m.DEEP)
    y += 34
    for linea in m.wrap(m.SANS, t.get("nota", ""), 18, ANCHO - 2 * MARGEN):
        y += 30
        cuerpo += m.text(m.SANS, linea, 18, MARGEN, y, m.MUTED)
    alto = int(y + 64)
    return m.svg(ANCHO, alto, cuerpo, m.PAPER), alto


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    carpeta = Path(sys.argv[1])
    origen = carpeta / "docs" / "tablas.toml"
    if not origen.exists():
        sys.exit(f"No existe {origen}. Corre antes make demo en {carpeta}.")
    with origen.open("rb") as f:
        tablas = tomllib.load(f)["tabla"]
    numero = carpeta.name.split("-", 1)[0]
    m = cargar_marca()
    for t in tablas:
        if not all(len(f) == len(t["columnas"]) for f in t["filas"]):
            sys.exit(f"La tabla '{t['id']}' tiene filas con distinta cantidad de columnas")
        try:
            svg, _ = dibujar(t, numero, m)
        except ValueError as e:
            sys.exit(f"Error: {e}")
        png = origen.with_name(f"tabla-{t['id']}.png")
        m.cairosvg.svg2png(bytestring=svg.encode(), write_to=str(png))
        print(f"Listo: {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
