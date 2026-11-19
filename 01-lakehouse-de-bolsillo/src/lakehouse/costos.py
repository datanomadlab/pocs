"""Modelo de costos. Funciones puras: reciben números y devuelven números.

Fuentes de las reglas de BigQuery:
- tamaño lógico por tipo: https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types#data_type_sizes
- cobro por demanda (bytes de las columnas referenciadas): https://cloud.google.com/bigquery/pricing
"""
from __future__ import annotations

from dataclasses import dataclass

TIB = 1024**4
GIB = 1024**3
GB = 1000**3
DIAS_MES = 30

BYTES_FIJOS = {"int64": 8, "double": 8, "timestamp[us]": 8}
BYTES_BASE_STRING = 2


def bytes_logicos(tipo: str, no_nulos: int, bytes_utf8: int = 0) -> int:
    """Bytes lógicos de una columna en BigQuery. Los NULL cuentan 0."""
    if no_nulos < 0 or bytes_utf8 < 0:
        raise ValueError("Los conteos no pueden ser negativos")
    if tipo == "string":
        return BYTES_BASE_STRING * no_nulos + bytes_utf8
    if tipo not in BYTES_FIJOS:
        raise ValueError(f"Tipo sin tamaño lógico definido: {tipo}")
    return BYTES_FIJOS[tipo] * no_nulos


def bytes_facturados(bytes_columnas: int, minimo_por_tabla: int) -> int:
    """BigQuery por demanda cobra un mínimo por tabla referenciada."""
    return max(bytes_columnas, minimo_por_tabla)


def costo_bq_consulta(bytes_fact: int, usd_por_tib: float) -> float:
    return bytes_fact / TIB * usd_por_tib


@dataclass(frozen=True)
class CostoMensual:
    almacenamiento: float
    computo: float

    @property
    def total(self) -> float:
        return self.almacenamiento + self.computo


def mensual_bigquery(bytes_por_ejecucion: int, ejecuciones_dia: float, bytes_almacenados: int,
                     precios: dict, con_capa_gratuita: bool = True) -> CostoMensual:
    """bytes_por_ejecucion: suma de bytes facturados de todas las consultas de una ejecución."""
    tib_mes = bytes_por_ejecucion * ejecuciones_dia * DIAS_MES / TIB
    gib = bytes_almacenados / GIB
    if con_capa_gratuita:
        tib_mes = max(0.0, tib_mes - precios["tib_gratis_mes"])
        gib = max(0.0, gib - precios["gib_gratis_mes"])
    return CostoMensual(almacenamiento=gib * precios["usd_por_gib_mes"],
                        computo=tib_mes * precios["usd_por_tib"])


def mensual_lakehouse(segundos_por_ejecucion: float, ejecuciones_dia: float, bytes_almacenados: int,
                      precios_bucket: dict, precios_computo: dict,
                      con_capa_gratuita: bool = True) -> CostoMensual:
    """DuckDB corriendo en un contenedor que se paga por segundo, leyendo desde un bucket."""
    segundos = segundos_por_ejecucion * ejecuciones_dia * DIAS_MES
    vcpu_s = segundos * precios_computo["vcpu"]
    gib_s = segundos * precios_computo["memoria_gib"]
    if con_capa_gratuita:
        vcpu_s = max(0.0, vcpu_s - precios_computo["vcpu_s_gratis_mes"])
        gib_s = max(0.0, gib_s - precios_computo["gib_s_gratis_mes"])
    computo = vcpu_s * precios_computo["usd_por_vcpu_s"] + gib_s * precios_computo["usd_por_gib_s"]
    return CostoMensual(almacenamiento=bytes_almacenados / GB * precios_bucket["usd_por_gb_mes"],
                        computo=computo)


def ahorro_pct(costo_base: float, costo_nuevo: float) -> float | None:
    """Porcentaje de ahorro respecto de costo_base. None si la base es 0 (no hay nada que ahorrar)."""
    if costo_base <= 0:
        return None
    return (costo_base - costo_nuevo) / costo_base * 100
