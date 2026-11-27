"""Línea de comandos del experimento: python -m pipeline <paso>."""
from __future__ import annotations

import argparse
import json
import shutil
import sys

import duckdb
import psycopg2

from . import config, contenedores, costos, datos, medir, reporte
from .formato import entero


def preparar() -> None:
    print("1/5 Descargando y limpiando los datos (Online Retail II, UCI)")
    datos.descargar()
    datos.descomprimir()
    d = datos.preparar()
    print(f"    {entero(d['filas que quedan'])} de {entero(d['filas del archivo'])} líneas de factura; "
          "el resto se descarta y se cuenta")


def medir_todo() -> None:
    try:
        medir.medir()
    finally:
        contenedores.borrar(config.CONTENEDOR_POSTGRES)
        for camino in config.CAMINOS:
            contenedores.borrar(f"pipeline03-{camino}")


def escribir_reporte() -> None:
    print("5/5 Escribiendo el reporte")
    if not config.MEDICION.exists():
        raise RuntimeError("No hay medición. Corre primero: make demo")
    medicion = json.loads(config.MEDICION.read_text(encoding="utf-8"))
    precios = costos.cargar(config.ESCENARIO)
    config.RESULTADOS.write_text(reporte.markdown(medicion, precios), encoding="utf-8")
    config.TABLAS.write_text(reporte.tablas(medicion, precios), encoding="utf-8")
    print("\n" + reporte.resumen(medicion, precios))
    print(f"\nReporte completo en {config.RESULTADOS.relative_to(config.RAIZ)}")


def destruir() -> None:
    contenedores.limpiar_todo()
    if config.DATOS.exists():
        shutil.rmtree(config.DATOS)
    print("Contenedores, imagen y datos locales borrados. En la nube no se creó nada")


PASOS = {"preparar": preparar, "medir": medir_todo, "reporte": escribir_reporte, "destruir": destruir}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paso", choices=[*PASOS, "demo"])
    paso = parser.parse_args().paso
    try:
        for nombre in (["preparar", "medir", "reporte"] if paso == "demo" else [paso]):
            PASOS[nombre]()
    except (RuntimeError, ValueError, duckdb.Error, psycopg2.Error) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
