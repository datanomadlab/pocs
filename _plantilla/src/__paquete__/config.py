"""Rutas del experimento. Lo que el lector quiera cambiar va aquí, en .env.example o en un .toml."""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data"
MEDICION = DATOS / "medicion.json"
RESULTADOS = RAIZ / "docs" / "resultados.md"
TABLAS = RAIZ / "docs" / "tablas.toml"

ETIQUETAS = ("medido", "estimado", "simulado", "modelo")
