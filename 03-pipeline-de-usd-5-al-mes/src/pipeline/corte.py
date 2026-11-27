"""Prueba 3: corre el job de dlt y lo mata en un punto exacto de la carga.

Un `docker kill` a ciegas casi siempre cae mientras dlt lee el origen, porque escribe todo al final y
en pocos milisegundos. Para probar también los momentos difíciles, el job se mata a sí mismo con
SIGKILL, que no se puede atrapar ni limpiar: es lo mismo que un corte, pero en el punto elegido.

CORTE elige el punto:
- lectura:  leyó el origen y no escribió nada en el destino.
- archivos: escribió los Parquet y no cerró la carga.
- avance:   guardó hasta dónde llegó y no alcanzó a registrar la carga.
"""
from __future__ import annotations

import os
import signal
import sys

from dlt.destinations.impl.filesystem.filesystem import FilesystemClient
from dlt.pipeline.pipeline import Pipeline

from . import job_dlt

PUNTOS = {
    "lectura": (Pipeline, "normalize"),
    "archivos": (FilesystemClient, "complete_load"),
    "avance": (FilesystemClient, "_store_load"),
}


def _matar(*_args, **_kwargs) -> None:
    os.kill(os.getpid(), signal.SIGKILL)


def main() -> int:
    clase, metodo = PUNTOS[os.environ["CORTE"]]
    setattr(clase, metodo, _matar)
    return job_dlt.main()


if __name__ == "__main__":
    sys.exit(main())
