"""Modelo de costos: funciones puras, sin acceso a datos. Precios en escenario.toml, cantidades en la medición.

Cada función recibe `capa`: True descuenta la capa gratuita, False cobra todo desde el primer segundo.
"""
from __future__ import annotations

import math
import statistics
import tomllib
from pathlib import Path

GIB = 2**30   # Google publica sus capas gratuitas en "GB" pero factura en GiB: se usa GiB en las dos
TIB = 2**40
GB = 1e9      # solo para Airbyte, que cobra por GB


def cargar(ruta: Path) -> dict:
    return tomllib.loads(ruta.read_text(encoding="utf-8"))


def segundos_facturados(segundos: float, p: dict) -> float:
    """Lo que Cloud Run cobra por una instancia: al menos un minuto, redondeado hacia arriba a 100 ms."""
    pasos = math.ceil(round(segundos / p["redondeo_s"], 6))
    return max(p["minimo_s"], pasos * p["redondeo_s"])


def cloud_run_mes(segundos_corrida: float, corridas: int, p: dict, capa: bool) -> float:
    facturados = segundos_facturados(segundos_corrida + p["arranque_s"], p) * corridas
    vcpu_s, gib_s = facturados * p["vcpu"], facturados * p["memoria_gib"]
    if capa:
        vcpu_s, gib_s = max(0.0, vcpu_s - p["vcpu_s_gratis_mes"]), max(0.0, gib_s - p["gib_s_gratis_mes"])
    return vcpu_s * p["usd_por_vcpu_s"] + gib_s * p["usd_por_gib_s"]


def scheduler_mes(jobs: int, p: dict, capa: bool) -> float:
    return max(0, jobs - (p["jobs_gratis"] if capa else 0)) * p["usd_por_job_mes"]


def bucket_mes(bytes_guardados: float, escrituras: float, lecturas: float, p: dict, capa: bool) -> float:
    gratis_bytes = p["gb_gratis_mes"] * GIB if capa else 0
    a = max(0.0, escrituras - (p["clase_a_gratis_mes"] if capa else 0))
    b = max(0.0, lecturas - (p["clase_b_gratis_mes"] if capa else 0))
    return (max(0.0, bytes_guardados - gratis_bytes) / GIB * p["usd_por_gib_mes"]
            + a / 1000 * p["usd_por_1000_clase_a"] + b / 1000 * p["usd_por_1000_clase_b"])


def registro_mes(bytes_imagen: float, p: dict, capa: bool) -> float:
    gratis = p["gb_gratis_mes"] * GIB if capa else 0
    return max(0.0, bytes_imagen - gratis) / GIB * p["usd_por_gib_mes"]


def fivetran_mes(mar: float, p: dict, capa: bool) -> float:
    """Plan gratuito si las filas activas caben; si no, la tarifa por tramos del plan Standard."""
    if capa and mar <= p["mar_gratis_mes"]:
        return 0.0
    if mar <= 0:
        return 0.0
    desde, base, por_millon = max((t for t in p["tramos"] if mar >= t[0]), key=lambda t: t[0])
    return base + (mar - desde) / 1e6 * por_millon


def airbyte_mes(bytes_movidos: float, p: dict) -> float:
    creditos = bytes_movidos * p["factor_volumen"] / GB * p["creditos_por_gb"]
    return p["usd_mes_minimo"] + max(0.0, creditos - p["creditos_incluidos"]) * p["usd_por_credito"]


def bigquery_mes(bytes_tablas: float, bytes_consultados: float, p: dict, capa: bool) -> float:
    gib = max(0.0, bytes_tablas / GIB - (p["gib_gratis_mes"] if capa else 0))
    tib = max(0.0, bytes_consultados / TIB - (p["tib_gratis_mes"] if capa else 0))
    return gib * p["usd_por_gib_mes"] + tib * p["usd_por_tib"]


def segundos_por_corrida(fijo: float, carga: float, publicar: float, factor: float) -> float:
    """SUPUESTO: cargar y publicar crecen en proporción a los datos; el arranque del contenedor no."""
    return fijo + (carga + publicar) * factor


def cantidades(medicion: dict) -> dict:
    """Lo que el modelo toma de la medición, con los datos medidos (factor 1)."""
    diarias = medicion["diarias"]
    med = statistics.median
    return {
        "fijo": med(d["dlt"]["segundos"] - d["dlt"]["segundos_job"] for d in diarias),
        "carga": med(d["dlt"]["segundos_carga"] for d in diarias),
        "publicar": med(d["dlt"]["segundos_publicar"] for d in diarias),
        "archivos_escritos": med(d["dlt"]["archivos_nuevos"] for d in diarias),
        "archivos_leidos": medicion["destino"]["archivos_crudo"],
        "bytes_bucket": medicion["destino"]["dlt"]["bytes"],
        "bytes_imagen": medicion["destino"]["imagen_bytes"],
        "mar": medicion["volumen_mes"]["filas"],
        "bytes_tocados": medicion["volumen_mes"]["bytes_tocados"],
        "bytes_tablas": medicion["volumen_mes"]["bytes_tablas"],
        "reportes": medicion["lineas"]["n_reportes"],
    }


def esta_arquitectura(q: dict, factor: float, precios: dict, capa: bool) -> dict:
    corridas = precios["modelo"]["corridas_mes"]
    segundos = segundos_por_corrida(q["fijo"], q["carga"], q["publicar"], factor)
    escrituras = (q["archivos_escritos"] + precios["bucket"]["listados_por_corrida"]) * corridas
    partes = {
        "cloud_run": cloud_run_mes(segundos, corridas, precios["cloud_run"], capa),
        "scheduler": scheduler_mes(1, precios["scheduler"], capa),
        "bucket": bucket_mes(q["bytes_bucket"] * factor, escrituras, q["archivos_leidos"] * corridas,
                             precios["bucket"], capa),
        "registro": registro_mes(q["bytes_imagen"], precios["registro"], capa),
    }
    return {"segundos": segundos, **partes, "total": sum(partes.values())}


def administradas(q: dict, factor: float, precios: dict, capa: bool) -> dict:
    corridas = precios["modelo"]["corridas_mes"]
    bq = bigquery_mes(q["bytes_tablas"] * factor, q["bytes_tablas"] * factor * q["reportes"] * corridas,
                      precios["bigquery"], capa)
    return {"bigquery": bq,
            "fivetran": fivetran_mes(q["mar"] * factor, precios["fivetran"], capa) + bq,
            "airbyte": airbyte_mes(q["bytes_tocados"] * factor, precios["airbyte"]) + bq}


def escenarios(medicion: dict, precios: dict) -> list[dict]:
    q = cantidades(medicion)
    out = []
    for e in precios["escenario"]:
        f = e["factor_datos"]
        out.append({**e,
                    "nuestra": {"con_capa": esta_arquitectura(q, f, precios, True),
                                "sin_capa": esta_arquitectura(q, f, precios, False)},
                    "administradas": {"con_capa": administradas(q, f, precios, True),
                                      "sin_capa": administradas(q, f, precios, False)}})
    return out
