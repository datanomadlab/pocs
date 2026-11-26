"""Cómo se escriben los números en todo lo que imprime o publica el experimento: formato español."""
from __future__ import annotations

# «Este valor o más»: la pieza aguantó hasta donde llegó la prueba. Va «>=» y no «≥» porque la fuente con
# que se dibujan las tablas y se graba la demo no trae ese símbolo, y todas las salidas dicen lo mismo.
O_MAS = ">= "

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


def decimal(valor: float, cifras: int = 1) -> str:
    return es(f"{valor:,.{cifras}f}")


def latencia(milisegundos: float) -> str:
    """Latencia medida en ms: un decimal bajo 10 ms, y en segundos desde 1.000 ms."""
    if milisegundos >= 1_000:
        return segundos(milisegundos / 1000)
    return (decimal(milisegundos, 1) if milisegundos < 10 else decimal(milisegundos, 0)) + " ms"


def segundos(valor: float) -> str:
    return (decimal(valor, 1) if valor < 10 else decimal(valor, 0)) + " s"


def por_segundo(tasa: int) -> str:
    return entero(tasa) + "/s"
