"""Lo poco de Docker que usa el experimento: el Postgres de origen, la imagen del job y sus corridas."""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from . import config


def docker(*args: str, revisar: bool = True, silencio: bool = True) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(["docker", *args], capture_output=silencio, text=True)
    except FileNotFoundError as e:
        raise RuntimeError("No encuentro Docker. Instálalo y déjalo corriendo antes de make demo") from e
    if revisar and r.returncode != 0:
        detalle = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or ["sin detalle"]
        raise RuntimeError(f"docker {args[0]} falló: {detalle[0]}")
    return r


def existe(nombre: str) -> bool:
    return bool(docker("ps", "-aq", "--filter", f"name=^{nombre}$").stdout.strip())


def crear_red() -> None:
    if not docker("network", "ls", "-q", "--filter", f"name=^{config.RED}$").stdout.strip():
        docker("network", "create", config.RED)


def levantar_postgres() -> None:
    """Postgres limpio en cada demo: sin volumen, los datos viven lo que vive el contenedor."""
    borrar(config.CONTENEDOR_POSTGRES)
    crear_red()
    docker("run", "-d", "--name", config.CONTENEDOR_POSTGRES, "--network", config.RED,
           "-p", f"127.0.0.1:{config.PUERTO_POSTGRES}:5432",
           "-e", f"POSTGRES_USER={config.USUARIO}", "-e", f"POSTGRES_PASSWORD={config.CLAVE}",
           "-e", f"POSTGRES_DB={config.BASE}", config.IMAGEN_POSTGRES)
    for _ in range(60):
        listo = docker("exec", config.CONTENEDOR_POSTGRES, "pg_isready", "-U", config.USUARIO,
                       "-d", config.BASE, "-h", "127.0.0.1", revisar=False)
        if listo.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("Postgres no respondió en 60 segundos")


def borrar(nombre: str) -> None:
    if existe(nombre):
        docker("rm", "-f", nombre)


def construir_imagen(carpeta: Path = config.RAIZ) -> None:
    docker("build", "-q", "-t", config.IMAGEN_JOB, str(carpeta))


def peso_imagen_bytes() -> int:
    """Peso de la imagen comprimida, que es lo que guarda y cobra un registro de contenedores."""
    r = subprocess.run(f"docker save {config.IMAGEN_JOB} | gzip -1 | wc -c", shell=True,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("No pude medir el peso de la imagen del job")
    return int(r.stdout.strip())


@dataclass(frozen=True)
class Corrida:
    camino: str
    corrida: str
    codigo: int       # código de salida del contenedor; 137 es muerte por memoria o por docker kill
    segundos: float   # desde que parte el contenedor hasta que termina: lo que cobraría Cloud Run
    salida: str


def _argumentos(camino: str, corrida: str, nombre: str, dsn: str, corte: str | None = None) -> list[str]:
    """El job corre con el límite de Cloud Run. Allá el disco del contenedor vive en memoria y
    cuenta contra los 512 MB; aquí se imita más estricto: todo es de solo lectura salvo /tmp, que es
    un tmpfs. Corre con el usuario
    de quien lanza la demo, para que lo que deje en data/ se pueda borrar sin permisos especiales.
    Con `corte`, el job de dlt se mata a sí mismo en ese punto de la carga (ver corte.py)."""
    config.BUCKET.mkdir(parents=True, exist_ok=True)
    usuario = ["--user", f"{os.getuid()}:{os.getgid()}"] if hasattr(os, "getuid") else []
    modulo = f"pipeline.job_{camino}" if corte is None else "pipeline.corte"
    # --init: el job no queda como proceso 1, que Linux protege de las señales que se manda a sí mismo.
    return ["--name", nombre, "--network", config.RED, "--init", *usuario,
            "--cpus", config.CPUS, "--memory", f"{config.MEMORIA_MB}m", "--memory-swap", f"{config.MEMORIA_MB}m",
            "--read-only", "--tmpfs", "/tmp",
            "-v", f"{config.BUCKET}:/bucket",
            "-e", f"ORIGEN={dsn}", "-e", "BUCKET=/bucket", "-e", f"CORRIDA={corrida}", "-e", f"CORTE={corte or ''}",
            config.IMAGEN_JOB, "python", "-m", modulo]


def correr_job(camino: str, corrida: str, corte: str | None = None, dsn: str = config.DSN_EN_RED) -> Corrida:
    nombre = f"pipeline03-{camino}"
    borrar(nombre)
    inicio = time.perf_counter()
    r = docker("run", *_argumentos(camino, corrida, nombre, dsn, corte), revisar=False)
    segundos = time.perf_counter() - inicio
    borrar(nombre)
    return Corrida(camino, corrida, r.returncode, segundos, (r.stdout or "") + (r.stderr or ""))


def correr_y_matar(camino: str, corrida: str, cuando) -> Corrida:
    """Parte el job, espera a que `cuando()` sea verdadero y lo mata sin aviso (docker kill)."""
    nombre = f"pipeline03-{camino}"
    borrar(nombre)
    inicio = time.perf_counter()
    docker("run", "-d", *_argumentos(camino, corrida, nombre, config.DSN_EN_RED))
    while not cuando():
        if docker("inspect", "-f", "{{.State.Running}}", nombre).stdout.strip() != "true":
            break   # terminó antes de que se cumpliera la condición: el corte no alcanzó a ocurrir
        time.sleep(0.05)
    docker("kill", nombre, revisar=False)
    segundos = time.perf_counter() - inicio
    codigo = int(docker("inspect", "-f", "{{.State.ExitCode}}", nombre).stdout.strip() or 0)
    salida = docker("logs", nombre, revisar=False)
    borrar(nombre)
    return Corrida(camino, corrida, codigo, segundos, (salida.stdout or "") + (salida.stderr or ""))


def limpiar_todo() -> None:
    for nombre in (config.CONTENEDOR_POSTGRES, *(f"pipeline03-{c}" for c in config.CAMINOS)):
        borrar(nombre)
    docker("network", "rm", config.RED, revisar=False)
    docker("rmi", "-f", config.IMAGEN_JOB, revisar=False)
