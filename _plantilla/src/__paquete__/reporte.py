"""Escribe docs/resultados.md, docs/tablas.toml y el resumen de la terminal desde la medición guardada.

Las tres salidas leen la misma medición para que la terminal, las imágenes del post y el reporte
digan siempre lo mismo. Cada métrica es {"nombre", "valor", "etiqueta"}, con el valor ya formateado
(ver formato.py) y la etiqueta en config.ETIQUETAS.
"""
from __future__ import annotations

from . import config
from .formato import fecha_larga

# El resumen se graba en el GIF de la demo: a este ancho se lee en un post sin hacer zoom.
ANCHO_RESUMEN = 68


def _validar(medicion: dict) -> list[dict]:
    metricas = medicion.get("metricas", [])
    for m in metricas:
        if m["etiqueta"] not in config.ETIQUETAS:
            raise ValueError(f"'{m['nombre']}': la etiqueta '{m['etiqueta']}' no es {', '.join(config.ETIQUETAS)}")
    return metricas


def linea(nombre: str, valor: str, etiqueta: str) -> str:
    """Una fila del resumen: nombre, valor y la etiqueta pegada al margen derecho."""
    return f"  {nombre:<22}{valor:<{ANCHO_RESUMEN - 24 - len(etiqueta)}}{etiqueta}"


def resumen(medicion: dict) -> str:
    metricas = _validar(medicion)
    if not metricas:
        return "Resumen: todavía no hay métricas"
    return "\n".join(["Resumen", ""] + [linea(m["nombre"], m["valor"], m["etiqueta"]) for m in metricas])


def markdown(medicion: dict) -> str:
    metricas = _validar(medicion)
    maq = medicion["maquina"]
    out = ["# Resultados", "",
           "> Archivo generado por `make demo`. No lo edites a mano: vuelve a correr la demo.", "",
           f"- **Máquina:** {maq['sistema']}, {maq['cpu']}, {maq['nucleos']} núcleos.",
           f"- **Fecha de la medición:** {medicion['fecha']}.", "",
           "| Métrica | Valor | Etiqueta |", "|---|---|---|"]
    out += [f"| {m['nombre']} | {m['valor']} | {m['etiqueta']} |" for m in metricas]
    return "\n".join(out) + "\n"


def _toml(texto: str) -> str:
    return '"' + str(texto).replace("\\", "\\\\").replace('"', '\\"') + '"'


def tablas(medicion: dict) -> str:
    """docs/tablas.toml: las tablas del post (Substack no tiene tablas), que dibuja `make tablas`."""
    metricas = _validar(medicion)
    filas = "".join(f"  [{_toml(m['nombre'])}, {_toml(m['valor'])}, {_toml(m['etiqueta'])}],\n" for m in metricas)
    return ("# Generado por make demo. No lo edites a mano.\n\n[[tabla]]\nid = \"resultados\"\n"
            "titulo = \"Resultados\"\ncolumnas = [\"Métrica\", \"Valor\", \"De dónde sale\"]\n"
            "etiquetas = [\"\", \"\", \"\"]\n"
            f"filas = [\n{filas}]\nnota = {_toml('Medido el ' + fecha_larga(medicion['fecha']) + '.')}\n")
