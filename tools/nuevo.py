#!/usr/bin/env python3
"""Parte un experimento nuevo desde _plantilla/, con todo lo que cada experimento necesita.

Uso, desde la raíz del repo (o `make nuevo NN=02`):
    python3 tools/nuevo.py 02
    python3 tools/nuevo.py 07 --titulo "Un título" --pregunta "¿Una pregunta?" [--paquete nombre]

Si el número ya está en lab.json, toma de ahí el título y la pregunta. Crea NN-titulo-en-minusculas/
con la plantilla (README, Makefile, código mínimo que ya corre, pruebas, diagrama y guion de la
demo), agrega la fila a la tabla del README raíz y pasa el experimento a en-construccion en lab.json.
No pisa una carpeta que ya existe.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PLANTILLA = "_plantilla"
PAQUETE = "__paquete__"
VACIAS = {"un", "una", "el", "la", "los", "las", "de", "del", "con", "para", "por", "y", "en", "mi", "tu", "al"}
FILA = re.compile(r"^\| (\d+) \|")


def _ascii(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def carpeta(numero: str, titulo: str) -> str:
    return f"{numero}-" + re.sub(r"[^a-z0-9]+", "-", _ascii(titulo).lower()).strip("-")


def paquete(nombre_carpeta: str) -> str:
    """El primer sustantivo del título: 02-agente-de-datos-con-mcp -> agente."""
    palabras = [p for p in nombre_carpeta.split("-")[1:] if p not in VACIAS and not p.isdigit()]
    if not palabras:
        raise ValueError("no pude elegir el nombre del paquete: pásalo con --paquete")
    return palabras[0]


def _entrada_lab(raiz: Path, numero: str) -> dict | None:
    lab = json.loads((raiz / "lab.json").read_text(encoding="utf-8"))
    return next((e for e in lab["experimentos"] if e["numero"] == numero), None)


def _rellenar(destino: Path, valores: dict[str, str]) -> None:
    for archivo in destino.rglob("*"):
        if not archivo.is_file():
            continue
        texto = archivo.read_text(encoding="utf-8")
        for clave, valor in valores.items():
            texto = texto.replace("{{" + clave + "}}", valor)
        archivo.write_text(texto, encoding="utf-8")


def _fila_readme(raiz: Path, numero: str, titulo: str, pregunta: str, nombre: str) -> None:
    ruta = raiz / "README.md"
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    filas = [i for i, l in enumerate(lineas) if FILA.match(l)]
    if any(FILA.match(lineas[i]).group(1) == numero for i in filas):
        return
    if not filas:
        raise ValueError("no encontré la tabla de experimentos en el README raíz")
    despues = max((i for i in filas if FILA.match(lineas[i]).group(1) < numero), default=filas[0] - 1)
    lineas.insert(despues + 1, f"| {numero} | [{titulo}]({nombre}/) | {pregunta} | En construcción | Pendiente |")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _en_construccion(raiz: Path, numero: str) -> None:
    """Cambia solo la línea del estado de ese experimento, sin reformatear el resto de lab.json."""
    ruta = raiz / "lab.json"
    texto = ruta.read_text(encoding="utf-8")
    inicio = texto.index(f'"numero": "{numero}"')
    siguiente = texto.find('"numero": "', inicio + 1)
    fin = len(texto) if siguiente == -1 else siguiente
    bloque = re.sub(r'"estado": "[a-z-]+"', '"estado": "en-construccion"', texto[inicio:fin], count=1)
    ruta.write_text(texto[:inicio] + bloque + texto[fin:], encoding="utf-8")
    json.loads(ruta.read_text(encoding="utf-8"))  # sigue siendo JSON válido


def crear(raiz: Path, numero: str, titulo: str | None = None, pregunta: str | None = None,
          nombre_paquete: str | None = None) -> Path:
    if not re.fullmatch(r"\d{2}", numero):
        raise ValueError(f"el número va con dos dígitos (02), no '{numero}'")
    entrada = _entrada_lab(raiz, numero)
    titulo = titulo or (entrada or {}).get("titulo")
    pregunta = pregunta or (entrada or {}).get("pregunta")
    if not titulo or not pregunta:
        raise ValueError(f"el {numero} no está en lab.json: pasa título y pregunta (--titulo, --pregunta)")
    nombre = carpeta(numero, titulo)
    existentes = [p.name for p in raiz.glob(f"{numero}-*")]
    if existentes:
        raise ValueError(f"ya existe {existentes[0]}/")
    pkg = nombre_paquete or paquete(nombre)
    if not pkg.isidentifier():
        raise ValueError(f"'{pkg}' no sirve como nombre de paquete de Python")

    destino = raiz / nombre
    shutil.copytree(raiz / PLANTILLA, destino, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    (destino / "src" / PAQUETE).rename(destino / "src" / pkg)
    _rellenar(destino, {"numero": numero, "titulo": titulo, "titulo_minusculas": titulo.lower(),
                        "pregunta": pregunta, "carpeta": nombre, "carpeta_sin_numero": nombre[3:],
                        "paquete": pkg})
    _fila_readme(raiz, numero, titulo, pregunta, nombre)
    if entrada:
        _en_construccion(raiz, numero)
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("numero")
    parser.add_argument("--titulo")
    parser.add_argument("--pregunta")
    parser.add_argument("--paquete")
    a = parser.parse_args()
    try:
        destino = crear(RAIZ, a.numero, a.titulo, a.pregunta, a.paquete)
    except (ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"Listo: {destino.name}/")
    if not _entrada_lab(RAIZ, a.numero):
        print("Falta su entrada en lab.json (numero, titulo, pregunta, stack, estado, en).")
    print(f"Sigue: cd {destino.name} && make setup && make demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
