"""Rutas y parámetros del experimento. Lo que el lector quiera cambiar va en .env (ver .env.example)."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data"
MEDICION = DATOS / "medicion.json"
RESULTADOS = RAIZ / "docs" / "resultados.md"
TABLAS = RAIZ / "docs" / "tablas.toml"
ESCENARIO = RAIZ / "escenario.toml"
SQL = RAIZ / "sql"

ETIQUETAS = ("medido", "estimado", "simulado", "modelo")


def _leer_env() -> dict[str, str]:
    """Variables de .env (si existe) por debajo de las del entorno."""
    valores: dict[str, str] = {}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip()
    return {**valores, **os.environ}


_ENV = _leer_env()

# El dataset: Online Retail II (UCI), CC BY 4.0.
URL_DATOS = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
DESCARGA = DATOS / "descarga"
ZIP = DESCARGA / "online_retail_ii.zip"
EXCEL = DESCARGA / "online_retail_II.xlsx"
HOJAS = ("Year 2009-2010", "Year 2010-2011")
VENTAS = DATOS / "ventas.parquet"        # las líneas de factura ya limpias
DESCARTES = DATOS / "descartes.json"     # cuántas filas sacó cada filtro

# La línea de tiempo: un año de historia y después los días que se simulan.
HISTORIA_HASTA = dt.date.fromisoformat(_ENV.get("HISTORIA_HASTA", "2010-11-30"))
DIAS = int(_ENV.get("DIAS", "30"))
DIAS_DE_PRUEBA = 5                       # días extra, con ventas: 3 para los cortes, 1 columna nueva, 1 dato malo

# El origen: Postgres en Docker. Usuario y clave solo valen para este contenedor local.
IMAGEN_POSTGRES = _ENV.get("IMAGEN_POSTGRES", "postgres:18.7")
PUERTO_POSTGRES = int(_ENV.get("PUERTO_POSTGRES", "54303"))
RED = "pipeline03"
CONTENEDOR_POSTGRES = "pipeline03-postgres"
BASE, USUARIO, CLAVE = "ventas", "lab", "lab"
DSN_LOCAL = f"postgresql://{USUARIO}:{CLAVE}@127.0.0.1:{PUERTO_POSTGRES}/{BASE}"
DSN_EN_RED = f"postgresql://{USUARIO}:{CLAVE}@{CONTENEDOR_POSTGRES}:5432/{BASE}"
TABLAS_ORIGEN = ("clientes", "productos", "facturas", "lineas")
LLAVES = {"clientes": "id_cliente", "productos": "codigo", "facturas": "id_factura", "lineas": "id_linea"}

# El job: la misma imagen que correría en Cloud Run, con el límite más chico que acepta un job.
IMAGEN_JOB = "pipeline03-job"
CPUS = _ENV.get("CPUS", "1")
MEMORIA_MB = int(_ENV.get("MEMORIA_MB", "512"))
BUCKET = DATOS / "bucket"                # en local, una carpeta; en la nube, un bucket
CAMINOS = ("dlt", "script")
