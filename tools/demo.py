#!/usr/bin/env python3
"""Graba la demo de un experimento como GIF de terminal, con la salida real de sus comandos.

Uso, desde la raíz del repo: `make demo-gif EXP=01-lakehouse-de-bolsillo`, o `make imagenes EXP=...`
para grabar la demo y después dibujar tablas y diagrama con la medición que quedó.

Lee docs/demo.toml, corre de verdad cada comando del guion dentro de la carpeta del experimento
y escribe docs/demo.gif. Nada de la salida se escribe a mano: las líneas y su orden son las que
imprimió el comando. Lo único que se edita es el tiempo: las esperas largas (una descarga, por
ejemplo) se acortan, y cuando eso pasa el GIF agrega un comentario con la duración real.
Las fuentes y los colores vienen del repo del sitio, igual que tools/diagrama.py.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

from diagrama import cargar_marca

ANCHO = 940
ALTO = 720
MARGEN = 28
BARRA = 44
TAM_FUENTE = 15
ALTO_LINEA = 22

MS_POR_TECLA = 55
ESPERA_MAX_S = 1.0       # una espera real más larga que esto se acorta a este valor
ENTRE_LINEAS_MIN_S = 0.08  # lo que se imprime de golpe aparece línea a línea para que se lea
ACORTADO_AVISO_S = 3.0   # si el GIF acorta más que esto, se agrega el comentario con la duración real
FINAL_S = 8.0

ETIQUETAS = ("medido", "estimado", "simulado", "modelo")


@dataclass(frozen=True)
class Linea:
    t: float
    texto: str


def grabar(comando: str, carpeta: Path) -> tuple[list[Linea], float]:
    """Corre el comando y devuelve cada línea de salida con el segundo en que apareció."""
    entorno = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    entorno |= {"PYTHONUNBUFFERED": "1", "NO_COLOR": "1", "TERM": "dumb"}
    inicio = time.monotonic()
    proc = subprocess.Popen(["bash", "-c", comando], cwd=carpeta, env=entorno, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lineas = [Linea(time.monotonic() - inicio, re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", l.rstrip()))
              for l in proc.stdout]
    if proc.wait() != 0:
        sys.exit(f"'{comando}' terminó con error; no se graba una demo que falla:\n"
                 + "\n".join(l.texto for l in lineas[-15:]))
    return lineas, time.monotonic() - inicio


def segundos(s: float) -> str:
    return f"{s:.0f} s" if s >= 10 else f"{s:.1f} s".replace(".", ",")


def linea_de_tiempo(pasos: list[dict], carpeta: Path) -> list[tuple[float, list[str]]]:
    """Lista de (duración del cuadro, pantalla completa). La pantalla es la lista de líneas."""
    cuadros: list[tuple[float, list[str]]] = []
    pantalla: list[str] = []

    def mostrar(duracion: float) -> None:
        cuadros.append((duracion, list(pantalla)))

    for paso in pasos:
        comando = paso["comando"]
        print(f"Grabando: {comando}")
        salida, real = grabar(comando, carpeta)
        pantalla.append("$ ")
        for i in range(0, len(comando), 2):
            pantalla[-1] = "$ " + comando[: i + 2]
            mostrar(2 * MS_POR_TECLA / 1000)
        mostrar(0.4)
        anterior, mostrado = 0.0, 0.0
        for linea in salida:
            espera = max(min(linea.t - anterior, ESPERA_MAX_S), ENTRE_LINEAS_MIN_S)
            cuadros[-1] = (cuadros[-1][0] + espera, cuadros[-1][1])
            mostrado += espera
            anterior = linea.t
            pantalla.append(linea.texto)
            mostrar(0)
        if real - mostrado > ACORTADO_AVISO_S:
            pantalla.append(f"# tardó {segundos(real)}; el video acorta las esperas")
            mostrar(0)
        cuadros[-1] = (cuadros[-1][0] + paso.get("pausa", 2.0), cuadros[-1][1])
        pantalla.append("")
    cuadros[-1] = (cuadros[-1][0] + FINAL_S, cuadros[-1][1])
    return [c for c in cuadros if c[0] > 0]


def tramos(texto: str, m, tenues: list[re.Pattern]) -> list[tuple[str, str]]:
    """Parte una línea en (texto, color)."""
    if texto.startswith("$ "):
        return [("$ ", m.MINT), (texto[2:], m.PAPER)]
    if texto.startswith("# ") or any(p.search(texto) for p in tenues):
        return [(texto, m.DARK_MUTED)]
    paso = re.match(r"^\d+/\d+ ", texto)
    if paso:
        return [(paso.group(), m.AMBER), (texto[paso.end():], m.PAPER)]
    colores = {"medido": m.MINT, "estimado": m.AMBER, "simulado": m.DARK_MUTED, "modelo": m.DARK_MUTED}
    etiqueta = re.search(rf"\b({'|'.join(ETIQUETAS)})$", texto)
    if etiqueta:
        return [(texto[: etiqueta.start()], m.PAPER), (etiqueta.group(), colores[etiqueta.group()])]
    return [(texto, m.PAPER)]


def fuente_ttf(m, destino: Path):
    """PIL no lee woff2: se convierte la mono de la marca a TTF una vez."""
    from fontTools.ttLib import TTFont
    from PIL import ImageFont
    ttf = destino / "ibm-plex-mono-500.ttf"
    if not ttf.exists():
        f = TTFont(m.FONTS / "ibm-plex-mono-500.woff2")
        f.flavor = None
        f.save(ttf)
    return ImageFont.truetype(str(ttf), TAM_FUENTE)


def dibujar(pantalla: list[str], titulo: str, m, fuente, tenues) -> "Image.Image":
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (ANCHO, ALTO), m.INK)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, ANCHO, BARRA], fill=m.DEEP)
    for i, color in enumerate((m.AMBER, m.MINT, m.DARK_MUTED)):
        x = MARGEN + i * 22
        d.ellipse([x - 6, BARRA / 2 - 6, x + 6, BARRA / 2 + 6], fill=color)
    d.text((ANCHO / 2, BARRA / 2), titulo, font=fuente, fill=m.DARK_MUTED, anchor="mm")
    filas = (ALTO - BARRA - 2 * MARGEN) // ALTO_LINEA
    for n, texto in enumerate(pantalla[-filas:]):
        x, y = MARGEN, BARRA + MARGEN + n * ALTO_LINEA
        for parte, color in tramos(texto, m, tenues):
            d.text((x, y), parte, font=fuente, fill=color)
            x += d.textlength(parte, font=fuente)
    return img


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    carpeta = Path(sys.argv[1]).resolve()
    guion_ruta = carpeta / "docs" / "demo.toml"
    if not guion_ruta.exists():
        sys.exit(f"No existe {guion_ruta}")
    with guion_ruta.open("rb") as f:
        guion = tomllib.load(f)
    m = cargar_marca()
    for comando in guion.get("preparar", []):
        print(f"Preparando (no sale en el GIF): {comando}")
        grabar(comando, carpeta)
    cuadros = linea_de_tiempo(guion["paso"], carpeta)

    from PIL import Image
    cache = Path(__file__).resolve().parent / ".cache"
    cache.mkdir(exist_ok=True)
    fuente = fuente_ttf(m, cache)
    tenues = [re.compile(p) for p in guion.get("tenue", [])]
    imagenes = [dibujar(p, guion["titulo"], m, fuente, tenues) for _, p in cuadros]
    paleta = imagenes[-1].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    gif = [i.quantize(palette=paleta, dither=Image.Dither.NONE) for i in imagenes]
    destino = carpeta / "docs" / "demo.gif"
    gif[0].save(destino, save_all=True, append_images=gif[1:], loop=0,
                duration=[round(s * 1000) for s, _ in cuadros])
    total = sum(s for s, _ in cuadros)
    print(f"Escribí {destino.relative_to(carpeta.parent)}: {len(gif)} cuadros, {total:.0f} s, "
          f"{destino.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
