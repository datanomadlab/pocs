"""Cálculos sobre lo que midió la sonda. Funciones puras: no tocan Docker ni relojes."""
from __future__ import annotations

from pathlib import Path

COMENTARIOS = ("//", "#", "/*", "*", "*/")


def perdidos(confirmados: int, unicos: int) -> int:
    """Eventos que el transporte aceptó y ninguna pantalla recibió."""
    return max(confirmados - unicos, 0)


def emitio_todo(fase: dict, tasa: int, segundos: int) -> bool:
    """El generador pudo emitir la tasa pedida: si no, la fase no dice nada de la pieza medida."""
    return fase["confirmados"] >= 0.99 * tasa * segundos and fase["atraso_generador_ms"] < 1_000


def aguanta(fase: dict, tasa: int, segundos: int, p99_max_ms: int) -> bool:
    """Una ruta aguanta una tasa si el generador pudo emitirla, no se perdió nada y el p99 cumple."""
    return emitio_todo(fase, tasa, segundos) and fase["perdidos"] == 0 and fase["latencia_ms"]["p99"] <= p99_max_ms


def corte(serie: list[list[int]], corte_ms: float, fin_carga_ms: float, tramo_ms: int, p99_max_ms: int) -> dict:
    """Qué vio la pantalla después de matar la pieza de entrega.

    serie: tramos [ms desde el inicio, eventos, p99 en ms, máximo en ms] de la sonda.
    congelada_s: desde el corte hasta que vuelve a llegar un evento.
    al_dia_s: desde el corte hasta el último tramo malo (sin eventos o con p99 sobre el máximo)
              mientras había carga. None si la carga terminó y la pantalla seguía atrasada.
    """
    durante = [t for t in serie if corte_ms <= t[0] <= fin_carga_ms]
    vacios = [t for t in durante if t[1] == 0]
    if not vacios:
        congelada_s = 0.0
    else:
        primer_vacio = vacios[0][0]
        vuelve = next((t[0] for t in durante if t[0] > primer_vacio and t[1] > 0), None)
        congelada_s = None if vuelve is None else max(vuelve - tramo_ms - corte_ms, 0) / 1000
    malos = [t for t in durante if t[1] == 0 or t[2] > p99_max_ms]
    if not malos:
        al_dia_s = 0.0
    elif malos[-1] is durante[-1]:
        al_dia_s = None
    else:
        al_dia_s = max(malos[-1][0] - corte_ms, 0) / 1000
    return {"congelada_s": congelada_s, "al_dia_s": al_dia_s,
            "atraso_max_s": max((t[3] for t in durante), default=0) / 1000}


def peor_corte(fases: list[dict]) -> dict:
    """De varios cortes, el que más daño hizo: primero el que no volvió, después el congelamiento
    más largo y, a igualdad, el que perdió más eventos."""
    def gravedad(fase: dict) -> tuple:
        congelada = fase["corte"]["congelada_s"]
        return (congelada is None, congelada or 0, fase["perdidos"], fase["duplicados"])
    return max(fases, key=gravedad)


def peor_por_columna(fases: list[dict]) -> dict:
    """El peor valor de cada dato entre varios cortes. Cada columna de la tabla es el peor caso de
    esa columna, aunque los peores no hayan ocurrido en el mismo corte."""
    def peor(valores: list) -> float | None:
        return None if any(v is None for v in valores) else max(valores)
    return {"perdidos": max(f["perdidos"] for f in fases), "duplicados": max(f["duplicados"] for f in fases),
            "desordenados": max(f["desordenados"] for f in fases),
            "corte": {k: peor([f["corte"][k] for f in fases]) for k in ("congelada_s", "al_dia_s", "atraso_max_s")}}


def lineas(archivo: Path) -> int:
    """Líneas con contenido: sin vacías ni comentarios de línea completa."""
    cuenta = 0
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        texto = linea.strip()
        if texto and not texto.startswith(COMENTARIOS):
            cuenta += 1
    return cuenta


def lineas_de(raiz: Path, plantillas: list[str], transporte: str) -> int:
    return sum(lineas(raiz / p.format(transporte=transporte)) for p in plantillas)
