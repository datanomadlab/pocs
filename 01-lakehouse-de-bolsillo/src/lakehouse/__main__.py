"""Línea de comandos del experimento: python -m lakehouse <paso>."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

from . import config, consultas, datos, reporte, tabla


def _peso(carpeta: Path, patron: str = "*") -> int:
    return sum(p.stat().st_size for p in carpeta.rglob(patron) if p.is_file())


def _cpu() -> str:
    if sys.platform == "darwin":
        import subprocess
        r = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return platform.processor() or platform.machine()


def preparar() -> None:
    meses = config.meses()
    print("1/4 Descargando datos públicos de NYC TLC")
    rutas = datos.descargar(meses)
    print("2/4 Creando la tabla Iceberg particionada por mes")
    tabla.crear_y_cargar(dict(zip(meses, rutas)))


def medir() -> None:
    print("3/4 Corriendo las consultas en DuckDB sobre Iceberg")
    meses = config.meses()
    esc = config.cargar_escenario()
    hilos, memoria = esc["computo"]["vcpu"], esc["computo"]["memoria_gib"]
    lista = config.cargar_consultas()
    con = consultas.conectar(tabla.abrir().metadata_location, hilos, memoria)
    medidas = consultas.medir(con, lista, meses[0])
    perfil = consultas.perfil_bytes(con)
    for consulta, medida in zip(lista, medidas):
        medida["bq_bytes_estimados"] = consultas.bytes_escaneados(consulta, perfil, meses[0])
    local = {
        "fecha": dt.date.today().isoformat(),
        "meses": meses,
        "filas": consultas.filas_totales(con),
        "hilos": hilos,
        "memoria_gib": memoria,
        "maquina": {"sistema": f"{platform.system()} {platform.release()}", "cpu": _cpu(),
                    "nucleos": os.cpu_count()},
        "versiones": {"duckdb": version("duckdb"), "pyiceberg": version("pyiceberg")},
        "crudos_bytes": sum(datos.ruta_mes(m).stat().st_size for m in meses),
        "bodega_bytes": _peso(config.BODEGA),
        "bq_bytes_logicos_total": sum(sum(cols.values()) for cols in perfil.values()),
        "consultas": medidas,
    }
    config.MEDICION_LOCAL.write_text(json.dumps(local, indent=2, ensure_ascii=False), encoding="utf-8")


def simular() -> None:
    from . import simulacion
    print("4/4 Simulando BigQuery: su SQL traducido y corrido sobre la misma tabla")
    meses = config.meses()
    esc = config.cargar_escenario()
    con = consultas.conectar(tabla.abrir().metadata_location, esc["computo"]["vcpu"],
                             esc["computo"]["memoria_gib"])
    resultado = simulacion.simular(con, config.cargar_consultas(), meses[0], consultas.perfil_bytes(con))
    sim = {"sqlglot": version("sqlglot"), "tolerancia": simulacion.TOLERANCIA, "consultas": resultado}
    config.MEDICION_SIM.write_text(json.dumps(sim, indent=2, ensure_ascii=False), encoding="utf-8")


def escribir_reporte() -> None:
    if not config.MEDICION_LOCAL.exists():
        raise RuntimeError("No hay medición local. Corre primero: make demo")
    local = json.loads(config.MEDICION_LOCAL.read_text(encoding="utf-8"))
    medido = (json.loads(config.MEDICION_BQ.read_text(encoding="utf-8"))
              if config.MEDICION_BQ.exists() else None)
    simulado = (json.loads(config.MEDICION_SIM.read_text(encoding="utf-8"))
                if config.MEDICION_SIM.exists() else None)
    texto = reporte.markdown(local, config.cargar_escenario(), medido, simulado)
    config.RESULTADOS.write_text(texto, encoding="utf-8")
    config.TABLAS.write_text(reporte.tablas(local, config.cargar_escenario(), simulado), encoding="utf-8")
    print(texto)
    print(f"\nGuardado en {config.RESULTADOS.relative_to(config.RAIZ)}")


def bq() -> None:
    from . import bigquery
    meses = config.meses()
    archivos = sorted((config.BODEGA).rglob("data/**/*.parquet"))
    if not archivos:
        raise RuntimeError("No hay tabla Iceberg. Corre primero: make demo")
    medido = bigquery.cargar_y_medir(archivos, config.cargar_consultas(), meses[0])
    config.MEDICION_BQ.write_text(json.dumps(medido, indent=2), encoding="utf-8")
    escribir_reporte()


def destruir() -> None:
    if os.environ.get("GCP_PROYECTO"):
        from . import bigquery
        print("Dataset de BigQuery borrado" if bigquery.borrar() else "No había dataset de BigQuery que borrar")
    if config.DATOS.exists():
        shutil.rmtree(config.DATOS)
    print("Datos locales borrados")


PASOS = {"preparar": preparar, "medir": medir, "simular": simular, "reporte": escribir_reporte, "bq": bq,
         "destruir": destruir}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paso", choices=[*PASOS, "demo"])
    paso = parser.parse_args().paso
    try:
        for nombre in (["preparar", "medir", "simular", "reporte"] if paso == "demo" else [paso]):
            PASOS[nombre]()
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
