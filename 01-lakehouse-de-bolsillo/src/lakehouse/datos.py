"""Descarga los Parquet públicos de NYC TLC (taxis amarillos). No se versionan."""
from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

from . import config


def ruta_mes(mes: str, carpeta: Path = config.CRUDOS) -> Path:
    return carpeta / f"yellow_tripdata_{mes}.parquet"


def descargar(meses: list[str], carpeta: Path = config.CRUDOS) -> list[Path]:
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []
    for mes in meses:
        destino = ruta_mes(mes, carpeta)
        if not destino.exists():
            url = f"{config.URL_BASE}/{destino.name}"
            print(f"  descargando {url}")
            parcial = destino.with_suffix(".parcial")
            try:
                with urllib.request.urlopen(url, timeout=120) as resp, parcial.open("wb") as f:
                    shutil.copyfileobj(resp, f)
            except OSError as e:
                parcial.unlink(missing_ok=True)
                raise RuntimeError(f"No pude descargar {url}: {e}") from e
            parcial.rename(destino)
        rutas.append(destino)
    return rutas
