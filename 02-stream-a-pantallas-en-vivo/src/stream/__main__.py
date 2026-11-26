"""Línea de comandos del experimento: python -m stream <paso>."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tomllib

from . import concurrencia, config, contenedores, costos, medir, reporte
from .formato import entero

IMAGEN = re.compile(r"^\s*image:\s*\S*?([\w.-]+):v?([\w.-]+)\s*$", re.MULTILINE)
NOMBRES = {"redpanda": "Redpanda", "nats": "NATS", "centrifugo": "Centrifugo", "redis": "Redis", "kinesis-mock": "kinesis-mock",
           "elasticmq-native": "ElasticMQ", "zilla": "Zilla", "emqx": "EMQX"}


def _cpu() -> str:
    if sys.platform == "darwin":
        r = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return platform.processor() or platform.machine()


def _versiones() -> dict[str, str]:
    """Las versiones salen de compose.yaml, que es donde están fijadas."""
    texto = (config.RAIZ / "compose.yaml").read_text(encoding="utf-8")
    return {NOMBRES[nombre]: version for nombre, version in IMAGEN.findall(texto) if nombre in NOMBRES}


def preparar() -> None:
    print("1/4 Construyendo y bajando las imágenes (la primera vez tarda unos minutos)")
    contenedores.version_docker()
    contenedores.construir()
    config.DATOS.mkdir(exist_ok=True)


def _maquina() -> dict:
    docker = contenedores.recursos_docker()
    return {"sistema": f"{platform.system()} {platform.release()}", "cpu": _cpu(), "nucleos": os.cpu_count(),
            "docker": contenedores.version_docker(), "docker_nucleos": docker["nucleos"],
            "docker_memoria_gb": docker["memoria_gb"]}


def medir_todo() -> None:
    p, rutas = config.parametros(), config.rutas()
    cuantas = "1 ruta" if len(rutas) == 1 else f"{len(rutas)} rutas, de a una"
    print(f"2/4 Midiendo {cuantas} (unos {(5 + 2 * p.cortes) * len(rutas)} minutos)")
    resultados = []
    for i, ruta in enumerate(rutas, 1):
        print(f"    {i}/{len(rutas)} {ruta.nombre}")
        resultados.append(medir.medir_ruta(ruta, p))
    hoy = dt.date.today().isoformat()
    resultados = [{**r, "fecha": hoy} for r in resultados]
    medicion = {
        "fecha": hoy, "rapido": p.rapido,
        "maquina": _maquina(),
        "parametros": {"tasa": p.tasa, "tasa_simulada": p.tasa_simulada, "emisores": p.emisores,
                       "cuentas": p.cuentas, "pantallas": p.pantallas, "espectadores": p.espectadores, "bytes": p.bytes,
                       "p99_max_ms": p.p99_max_ms, "cortes": p.cortes, "sesion_ms": p.sesion_ms},
        "versiones": _versiones(), "rutas": resultados,
    }
    medicion["rutas"] = combinar(_anterior(medicion), resultados, [r.id for r in config.rutas(todas=True)])
    medicion["fecha"] = fecha_principal(medicion["rutas"])
    config.MEDICION.write_text(json.dumps(medicion, indent=2, ensure_ascii=False), encoding="utf-8")


def _anterior(medicion: dict) -> list[dict]:
    """Las rutas de la medición guardada, si se midieron con los mismos parámetros que esta corrida."""
    if not config.MEDICION.exists():
        return []
    guardada = json.loads(config.MEDICION.read_text(encoding="utf-8"))
    iguales = guardada.get("parametros") == medicion["parametros"] and guardada.get("rapido") == medicion["rapido"]
    # Cada ruta conserva el día en que se midió; las de una medición anterior a este campo, el de esa medición.
    return [{"fecha": guardada["fecha"], **r} for r in guardada["rutas"]] if iguales else []


def fecha_principal(rutas: list[dict]) -> str:
    """El día en que se midió la mayoría de las rutas. Las demás se nombran aparte en el reporte."""
    return statistics.mode(sorted(r["fecha"] for r in rutas))


def combinar(anteriores: list[dict], nuevas: list[dict], orden: list[str]) -> list[dict]:
    """Con RUTAS se mide solo una parte: esas rutas reemplazan a las guardadas y el resto se conserva."""
    por_id = {r["id"]: r for r in anteriores} | {r["id"]: r for r in nuevas}
    return [por_id[i] for i in orden if i in por_id]


def nucleos_medidos(medicion: dict) -> dict:
    """Los núcleos que usó cada pieza a la tasa nominal, promediando las rutas medidas donde aparece."""
    entrega: dict[str, list[float]] = {}
    transporte: dict[str, list[float]] = {}
    for r in medicion["rutas"]:
        usados = r.get("nominal", {}).get("nucleos")
        if r["etiqueta"] != "medido" or not usados:
            continue
        entrega.setdefault(r["entrega"], []).append(usados["entrega"])
        transporte.setdefault(r["transporte"], []).append(usados["transporte"])
    return {"tasa": medicion["parametros"]["tasa"],
            "entrega": {k: statistics.mean(v) for k, v in entrega.items()},
            "transporte": {k: statistics.mean(v) for k, v in transporte.items()}}


def _cargar_medicion() -> dict:
    if not config.MEDICION.exists():
        raise RuntimeError("No hay medición. Corre primero: make demo")
    return json.loads(config.MEDICION.read_text(encoding="utf-8"))


def _modelo(archivo, medicion: dict) -> dict | None:
    """El modelo de costos con un archivo de escenario, o None si falta medir alguna pieza."""
    medidos = nucleos_medidos(medicion)
    if "centrifugo" not in medidos["entrega"] or "go" not in medidos["entrega"]:
        return None
    return costos.modelo(tomllib.loads(archivo.read_text(encoding="utf-8")), medidos)


def calcular_costos() -> None:
    print("3/4 Calculando el costo mensual de cada camino")
    medicion = _cargar_medicion()
    modelo = _modelo(config.ESCENARIO, medicion)
    if modelo is None:
        print("    Sin costos: el modelo necesita medida al menos una ruta con Go y una con Centrifugo")
        medicion.pop("costos", None)
    else:
        medicion["costos"] = modelo
    config.MEDICION.write_text(json.dumps(medicion, indent=2, ensure_ascii=False), encoding="utf-8")


def costos_locales() -> None:
    """El mismo modelo con escenario.local.toml. Sale a la terminal y a data/, que git ignora:
    nada de lo que pongas en ese archivo llega a docs/ ni al repo."""
    if not config.ESCENARIO_LOCAL.exists():
        raise RuntimeError("No existe escenario.local.toml. Copia escenario.toml con ese nombre y pon tus cifras")
    medicion = _cargar_medicion()
    modelo = _modelo(config.ESCENARIO_LOCAL, medicion)
    if modelo is None:
        raise RuntimeError("Falta medir al menos una ruta con Go y una con Centrifugo: make demo")
    texto = reporte.costos_markdown({**medicion, "costos": modelo})
    config.COSTOS_LOCALES.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Guardado en {config.COSTOS_LOCALES.relative_to(config.RAIZ)} (no se sube)")


def _con_concurrencia(medicion: dict) -> dict:
    """La medición más lo que dejó `make concurrencia`, si se corrió."""
    if not config.CONCURRENCIA.exists():
        return medicion
    return {**medicion, "concurrencia": json.loads(config.CONCURRENCIA.read_text(encoding="utf-8"))}


def escribir_reporte() -> None:
    print("4/4 Escribiendo el reporte")
    medicion = _con_concurrencia(_cargar_medicion())
    config.RESULTADOS.write_text(reporte.markdown(medicion), encoding="utf-8")
    config.TABLAS.write_text(reporte.tablas(medicion), encoding="utf-8")
    print("\n" + reporte.resumen(medicion))
    print(f"Reporte completo en {config.RESULTADOS.relative_to(config.RAIZ)}")


def medir_concurrencia() -> None:
    concurrencia.correr(_maquina())
    # Las tablas de concurrencia van al mismo reporte que las de make demo, que necesita su medición.
    if not config.CONCURRENCIA.exists():
        return
    if not config.MEDICION.exists():
        print("Para llevar estas tablas a docs/resultados.md corre make demo: el reporte parte de esa medición.")
        return
    medicion = _con_concurrencia(_cargar_medicion())
    config.RESULTADOS.write_text(reporte.markdown(medicion), encoding="utf-8")
    config.TABLAS.write_text(reporte.tablas(medicion), encoding="utf-8")
    print(f"Tablas en {config.RESULTADOS.relative_to(config.RAIZ)}")


def destruir() -> None:
    contenedores.bajar_todo(imagenes=True)
    if config.DATOS.exists():
        shutil.rmtree(config.DATOS)
    print("Contenedores, volúmenes, imágenes propias y datos locales borrados. Nada corre en la nube.")


PASOS = {"preparar": preparar, "medir": medir_todo, "costos": calcular_costos, "reporte": escribir_reporte,
         "local": costos_locales, "concurrencia": medir_concurrencia, "destruir": destruir}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paso", choices=[*PASOS, "demo"])
    paso = parser.parse_args().paso
    try:
        for nombre in (["preparar", "medir", "costos", "reporte"] if paso == "demo" else [paso]):
            PASOS[nombre]()
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
