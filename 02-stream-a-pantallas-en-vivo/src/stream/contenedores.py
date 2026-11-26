"""Todo lo que habla con Docker: levantar una ruta, correr el generador y la sonda, y leer el uso de CPU."""
from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass

from . import config

PERFILES_TODOS = [*config.DESTINOS, *config.ENTREGAS, "herramientas"]


class ErrorDocker(RuntimeError):
    pass


@dataclass(frozen=True)
class Compose:
    """docker compose con los perfiles y variables de una ruta."""
    ruta: config.Ruta
    sesion_ms: str = ""

    def _base(self) -> list[str]:
        return ["docker", "compose", "--profile", self.ruta.transporte, "--profile", self.ruta.entrega,
                "--profile", "herramientas"]

    def _entorno(self) -> dict[str, str]:
        return {**os.environ, "TRANSPORTE": self.ruta.transporte,
                "DESTINO_LECTOR": config.DESTINOS[self.ruta.transporte],
                "SESION_MS": self.ruta.sesion_ms or self.sesion_ms}

    def correr(self, *args: str, timeout: int = 300) -> str:
        try:
            r = subprocess.run([*self._base(), *args], cwd=config.RAIZ, env=self._entorno(),
                               capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise ErrorDocker(f"docker compose {' '.join(args[:4])} no terminó en {timeout} s") from None
        if r.returncode != 0:
            raise ErrorDocker(f"docker compose {' '.join(args[:3])} falló: {r.stderr.strip()[-400:]}")
        return r.stdout

    def abrir(self, *args: str) -> subprocess.Popen:
        return subprocess.Popen([*self._base(), *args], cwd=config.RAIZ, env=self._entorno(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def herramienta(self, nombre: str, *args: str) -> list[str]:
        return ["run", "--rm", "-T", nombre, *args]

    def id(self, servicio: str) -> str:
        identificador = self.correr("ps", "-q", servicio).strip()
        if not identificador:
            raise ErrorDocker(f"el servicio {servicio} no está corriendo")
        return identificador.splitlines()[0]


def construir() -> None:
    """Construye las imágenes propias y baja las demás. Lo que tarda la primera vez."""
    base = ["docker", "compose"] + [x for p in PERFILES_TODOS for x in ("--profile", p)]
    for paso in (["build", "--quiet"], ["pull", "--quiet", "--ignore-buildable"]):
        r = subprocess.run([*base, *paso], cwd=config.RAIZ, capture_output=True, text=True)
        if r.returncode != 0:
            raise ErrorDocker(f"docker compose {paso[0]} falló: {r.stderr.strip()[-400:]}")


def bajar_todo(imagenes: bool = False) -> None:
    base = ["docker", "compose"] + [x for p in PERFILES_TODOS for x in ("--profile", p)]
    extra = ["--rmi", "local"] if imagenes else []
    subprocess.run([*base, "down", "--volumes", "--remove-orphans", *extra], cwd=config.RAIZ,
                   capture_output=True, text=True)


def matar_y_levantar(identificador: str) -> None:
    """Mata el proceso sin aviso (SIGKILL) y lo vuelve a levantar de inmediato, como haría un orquestador."""
    for accion in ("kill", "start"):
        r = subprocess.run(["docker", accion, identificador], capture_output=True, text=True)
        if r.returncode != 0:
            raise ErrorDocker(f"docker {accion} falló: {r.stderr.strip()}")


def version_docker() -> str:
    r = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True)
    if r.returncode != 0:
        raise ErrorDocker("Docker no responde. Abre Docker Desktop (o el servicio de Docker) y vuelve a correr make demo")
    return r.stdout.strip()


def recursos_docker() -> dict:
    r = subprocess.run(["docker", "info", "--format", "{{.NCPU}} {{.MemTotal}}"], capture_output=True, text=True)
    nucleos, memoria = r.stdout.split()
    return {"nucleos": int(nucleos), "memoria_gb": round(int(memoria) / 2**30, 1)}


# --- Uso de CPU y memoria, leído de la API de Docker ------------------------------------------
# `docker stats` muestra un porcentaje instantáneo. Para saber cuánta CPU gastó un contenedor
# durante una fase se lee el contador acumulado antes y después, y se divide por el tiempo.

class _ConexionUnix(http.client.HTTPConnection):
    def __init__(self, ruta: str):
        super().__init__("localhost", timeout=10)
        self._ruta = ruta

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self._ruta)


def _socket_docker() -> str:
    r = subprocess.run(["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
                       capture_output=True, text=True)
    host = r.stdout.strip()
    if not host.startswith("unix://"):
        raise ErrorDocker("solo sé leer el uso de CPU de un Docker local (socket unix)")
    return host.removeprefix("unix://")


@dataclass(frozen=True)
class Lectura:
    cpu_ns: int
    memoria_bytes: int
    instante: float


def leer_uso(identificador: str) -> Lectura:
    conexion = _ConexionUnix(_socket_docker())
    try:
        conexion.request("GET", f"/containers/{identificador}/stats?stream=false&one-shot=true")
        respuesta = conexion.getresponse()
        if respuesta.status != 200:
            raise ErrorDocker(f"la API de Docker respondió {respuesta.status} al pedir el uso del contenedor")
        datos = json.loads(respuesta.read())
    finally:
        conexion.close()
    return Lectura(cpu_ns=datos["cpu_stats"]["cpu_usage"]["total_usage"],
                   memoria_bytes=datos.get("memory_stats", {}).get("usage", 0), instante=time.monotonic())


def nucleos_usados(antes: Lectura, despues: Lectura) -> float:
    """Núcleos ocupados en promedio entre dos lecturas."""
    return (despues.cpu_ns - antes.cpu_ns) / 1e9 / (despues.instante - antes.instante)
