"""Cómo se escriben los números en todo lo que imprime o publica el experimento: formato español."""
from __future__ import annotations

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")


def es(texto: str) -> str:
    """Pasa un número formateado a la inglesa (1,234.5) a formato español (1.234,5)."""
    return texto.translate(str.maketrans(",.", ".,"))


def entero(n: int) -> str:
    return es(f"{n:,}")


def ms(segundos: float) -> str:
    return es(f"{segundos * 1000:,.0f}") + " ms"


def mb(b: float) -> str:
    return es(f"{b / 1e6:,.0f}") + " MB"


def usd_corto(valor: float) -> str:
    """Dólares para una imagen o un post: sin centavos salvo en montos menores a 1."""
    if valor == 0:
        return "USD 0"
    if valor < 1:
        return "USD " + es(f"{valor:.3f}".rstrip("0"))
    return "USD " + es(f"{valor:,.0f}")


def fecha_larga(iso: str) -> str:
    """2026-11-19 -> 19 de noviembre de 2026."""
    anio, mes, dia = (int(x) for x in iso.split("-"))
    return f"{dia} de {MESES[mes - 1]} de {anio}"


def seg(segundos: float) -> str:
    """Segundos con un decimal: 2,6 s."""
    return es(f"{segundos:,.1f}") + " s"


def porcentaje(fraccion: float) -> str:
    """0,153 -> 15 %."""
    return es(f"{fraccion * 100:,.0f}") + " %"


def usd(valor: float) -> str:
    """Dólares de un modelo de costos: centavos bajo 10, sin centavos sobre 10. Sin precisión falsa."""
    if valor == 0:
        return "USD 0"
    if valor < 0.01:
        return "menos de USD 0,01"
    if valor < 10:
        return "USD " + es(f"{valor:,.2f}")
    return "USD " + es(f"{valor:,.0f}")
