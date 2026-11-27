"""Línea de comandos del experimento: python -m {{paquete}} <paso>."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys

from . import config, reporte


def _cpu() -> str:
    if sys.platform == "darwin":
        r = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return platform.processor() or platform.machine()


def preparar() -> None:
    print("1/3 Descargando los datos")  # por completar: descarga con un script, sin bajar lo que ya está
    config.DATOS.mkdir(exist_ok=True)


def medir() -> None:
    print("2/3 Midiendo")  # por completar: cada métrica con su etiqueta
    medicion = {
        "fecha": dt.date.today().isoformat(),
        "maquina": {"sistema": f"{platform.system()} {platform.release()}", "cpu": _cpu(),
                    "nucleos": os.cpu_count()},
        "metricas": [],
    }
    config.MEDICION.write_text(json.dumps(medicion, indent=2, ensure_ascii=False), encoding="utf-8")


def escribir_reporte() -> None:
    print("3/3 Escribiendo el reporte")
    if not config.MEDICION.exists():
        raise RuntimeError("No hay medición. Corre primero: make demo")
    medicion = json.loads(config.MEDICION.read_text(encoding="utf-8"))
    config.RESULTADOS.write_text(reporte.markdown(medicion), encoding="utf-8")
    config.TABLAS.write_text(reporte.tablas(medicion), encoding="utf-8")
    print("\n" + reporte.resumen(medicion))
    print(f"\nReporte completo en {config.RESULTADOS.relative_to(config.RAIZ)}")


def destruir() -> None:
    if config.DATOS.exists():
        shutil.rmtree(config.DATOS)
    print("Datos locales borrados")  # por completar: si se crea algo en la nube, se borra aquí


PASOS = {"preparar": preparar, "medir": medir, "reporte": escribir_reporte, "destruir": destruir}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paso", choices=[*PASOS, "demo"])
    paso = parser.parse_args().paso
    try:
        for nombre in (["preparar", "medir", "reporte"] if paso == "demo" else [paso]):
            PASOS[nombre]()
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
