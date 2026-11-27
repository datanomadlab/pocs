"""La medición completa: historia, carga inicial, los días simulados y las pruebas. Escribe data/medicion.json."""
from __future__ import annotations

import datetime as dt
import importlib.metadata
import json
import os
import platform
import subprocess
import sys

from . import config, contenedores, destino, origen, pruebas
from .formato import entero, seg

CADA_CUANTOS_DIAS = 5   # la terminal muestra un día de cada tantos, para que la demo se lea


def _cpu() -> str:
    if sys.platform == "darwin":
        r = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return platform.processor() or platform.machine()


def _versiones(con) -> dict[str, str]:
    paquetes = {p: importlib.metadata.version(p) for p in ("dlt", "duckdb", "psycopg2-binary", "pyarrow")}
    docker = contenedores.docker("version", "--format", "{{.Server.Version}}").stdout.strip()
    return {**paquetes, "postgres": origen.version(con), "python": platform.python_version(), "docker": docker}


def _archivos_dlt() -> int:
    return destino.peso("dlt")["archivos"] if (config.BUCKET / "dlt").exists() else 0


def _corrida_dlt(b: pruebas.Banco, corrida: str) -> dict:
    antes = _archivos_dlt()
    r = b.correr("dlt", corrida)
    rastro = destino.rastro(corrida) or {}
    if r.codigo != 0:
        raise RuntimeError(f"La corrida {corrida} de dlt falló (código {r.codigo}): {r.salida.strip()[-300:]}")
    return {"segundos": r.segundos, "segundos_job": rastro["segundos"], "segundos_carga": rastro["segundos_carga"],
            "segundos_publicar": rastro["segundos_publicar"], "filas": sum(rastro["filas"].values()),
            "memoria_mb": rastro["memoria_max_mb"], "archivos_nuevos": _archivos_dlt() - antes}


def _corrida_script(b: pruebas.Banco, corrida: str) -> dict:
    r = b.correr("script", corrida)
    if r.codigo != 0:
        raise RuntimeError(f"La corrida {corrida} del script falló (código {r.codigo}): {r.salida.strip()[-300:]}")
    return {"segundos": r.segundos, "filas": sum(destino.filas("script").values())}


def preparar_origen():
    print(f"2/5 Levantando Postgres y cargando la historia (hasta el {config.HISTORIA_HASTA})")
    contenedores.levantar_postgres()
    contenedores.construir_imagen()
    con = origen.conectar()
    origen.crear_esquema(con)
    primero = dt.date.fromisoformat("2009-12-01")
    origen.aplicar(con, primero, config.HISTORIA_HASTA)
    print(f"    {entero(sum(origen.contar(con).values()))} filas en cuatro tablas")
    return con


def simular(b: pruebas.Banco, dias: list[dt.date]) -> tuple[dict, list[dict]]:
    print(f"3/5 Carga inicial y {len(dias)} días con ventas, una corrida diaria por camino")
    inicial = {"dlt": _corrida_dlt(b, "historia"), "script": _corrida_script(b, "historia")}
    print(f"    carga inicial: dlt {seg(inicial['dlt']['segundos'])} · script {seg(inicial['script']['segundos'])}")
    diarias = []
    for i, dia in enumerate(dias, 1):
        tocadas = origen.aplicar(b.con, dia, dia)
        d = {"dia": dia.isoformat(), "tocadas": sum(tocadas.values()),
             "dlt": _corrida_dlt(b, dia.isoformat()), "script": _corrida_script(b, dia.isoformat())}
        d["igual"] = {c: b.igual(c) for c in config.CAMINOS}
        diarias.append(d)
        if i % CADA_CUANTOS_DIAS == 0 or i == len(dias):
            print(f"    día {i:>2} de {len(dias)} · {entero(d['tocadas'])} filas nuevas o cambiadas · "
                  f"dlt {seg(d['dlt']['segundos'])} · script {seg(d['script']['segundos'])}")
    return inicial, diarias


def incremental(diarias: list[dict], total_origen: int) -> dict:
    """1. La corrida diaria mueve solo lo nuevo y lo que cambió, y el destino queda igual al origen."""
    exactos = sum(d["dlt"]["filas"] == d["tocadas"] for d in diarias)
    iguales = {c: sum(d["igual"][c] for d in diarias) for c in config.CAMINOS}
    n = len(diarias)
    return {
        "dlt": pruebas.resultado(exactos == n and iguales["dlt"] == n,
                                 f"movió justo lo nuevo o cambiado en {exactos} de {n} días; mismas filas, "
                                 f"fechas y montos que el origen en {iguales['dlt']} de {n}"),
        "script": pruebas.resultado(False, f"copia las tablas completas cada día ({entero(total_origen)} filas "
                                           f"al final); mismas filas, fechas y montos que el origen en {iguales['script']} de {n}"),
    }


def correr_pruebas(b: pruebas.Banco, diarias: list[dict]) -> tuple[list[dict], dict]:
    print("4/5 Las siete pruebas")
    lista = [{"id": 1, "nombre": "Carga incremental",
              **incremental(diarias, sum(origen.contar(b.con).values()))}]
    extra = {}
    for numero, nombre, prueba in pruebas.PRUEBAS:
        res, detalle = prueba(b)
        lista.append({"id": numero, "nombre": nombre, **res})
        extra[numero] = detalle
    corto = {"pasa con código propio": "pasa, con código"}
    for p in lista:
        dlt, script = (corto.get(p[c]["resultado"], p[c]["resultado"]) for c in config.CAMINOS)
        print(f"    {p['id']} {p['nombre']:<28} dlt: {dlt:<17} script: {script}")
    return lista, extra


def lineas_de_codigo() -> dict[str, int]:
    """Líneas que hay que mantener por camino, sin contar vacías ni comentarios."""
    def contar(rutas) -> int:
        return sum(1 for r in rutas for l in r.read_text(encoding="utf-8").splitlines()
                   if l.strip() and not l.strip().startswith(("#", "--")))
    src, sql = config.RAIZ / "src" / "pipeline", config.SQL
    reportes = sorted((sql / "reportes").glob("*.sql"))
    return {"dlt": contar([src / "job_dlt.py", src / "vistas.py", sql / "vigente.sql",
                           *sorted((sql / "pruebas").glob("*.sql"))]),
            "script": contar([src / "job_script.py"]),
            "reportes": contar(reportes), "n_reportes": len(reportes)}


def medir() -> None:
    con = preparar_origen()
    total = config.DIAS + config.DIAS_DE_PRUEBA
    dias = origen.dias_con_ventas(config.HISTORIA_HASTA + dt.timedelta(days=1), total)
    if len(dias) < total:
        raise ValueError(f"El dataset solo tiene {len(dias)} días con ventas después de {config.HISTORIA_HASTA}")
    b = pruebas.Banco(con, iter(dias[config.DIAS:]))
    inicial, diarias = simular(b, dias[:config.DIAS])
    volumen = origen.volumen_desde(con, dias[0])
    pesos = {c: destino.peso(c) for c in config.CAMINOS}
    archivos_crudo = len(list((config.BUCKET / "dlt" / "crudo").rglob("*.parquet")))
    lista, extra = correr_pruebas(b, diarias)
    medicion = {
        "fecha": dt.date.today().isoformat(),
        "maquina": {"sistema": f"{platform.system()} {platform.release()}", "cpu": _cpu(), "nucleos": os.cpu_count()},
        "limite": {"cpus": config.CPUS, "memoria_mb": config.MEMORIA_MB},
        "versiones": _versiones(con),
        "datos": json.loads(config.DESCARTES.read_text(encoding="utf-8")),
        "historia_hasta": config.HISTORIA_HASTA.isoformat(),
        "dias": [dias[0].isoformat(), dias[config.DIAS - 1].isoformat()],
        "inicial": inicial, "diarias": diarias, "volumen_mes": volumen,
        "destino": {**pesos, "archivos_crudo": archivos_crudo, "imagen_bytes": contenedores.peso_imagen_bytes()},
        "pruebas": lista, "pruebas_detalle": extra, "lineas": lineas_de_codigo(),
    }
    config.MEDICION.write_text(json.dumps(medicion, indent=2, ensure_ascii=False), encoding="utf-8")
