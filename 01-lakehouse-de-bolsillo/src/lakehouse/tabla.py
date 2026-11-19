"""Crea la tabla Iceberg (particionada por mes) y carga los Parquet de origen."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from pyiceberg.catalog import Catalog
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.table import Table
from pyiceberg.transforms import MonthTransform
from pyiceberg.types import DoubleType, LongType, NestedField, StringType, TimestampType

from . import config

_TIPOS = {pa.int64(): LongType(), pa.float64(): DoubleType(), pa.string(): StringType(),
          pa.timestamp("us"): TimestampType()}


def catalogo(ruta_db: Path = config.CATALOGO, bodega: Path = config.BODEGA) -> Catalog:
    bodega.mkdir(parents=True, exist_ok=True)
    return SqlCatalog("local", uri=f"sqlite:///{ruta_db}", warehouse=f"file://{bodega}")


def esquema_iceberg() -> Schema:
    campos = [NestedField(i, campo.name, _TIPOS[campo.type], required=False)
              for i, campo in enumerate(config.ESQUEMA, start=1)]
    return Schema(*campos)


def rango_mes(mes: str) -> tuple[dt.datetime, dt.datetime]:
    anio, numero = (int(x) for x in mes.split("-"))
    inicio = dt.datetime(anio, numero, 1)
    fin = dt.datetime(anio + numero // 12, numero % 12 + 1, 1)
    return inicio, fin


def normalizar(tabla: pa.Table, mes: str) -> pa.Table:
    """Renombra y tipa las columnas, y descarta viajes cuyo inicio no cae en el mes del archivo.

    Los archivos de TLC traen un puñado de filas con fechas imposibles (2002, 2009...).
    Si se cargan, crean particiones basura.
    """
    columnas = [tabla[origen].cast(tipo) for origen, (_, tipo) in config.COLUMNAS.items()]
    limpia = pa.Table.from_arrays(columnas, schema=config.ESQUEMA)
    inicio, fin = rango_mes(mes)
    dentro = pc.and_(pc.greater_equal(limpia["inicio"], pa.scalar(inicio, pa.timestamp("us"))),
                     pc.less(limpia["inicio"], pa.scalar(fin, pa.timestamp("us"))))
    return limpia.filter(dentro)


def crear_y_cargar(rutas: dict[str, Path], cat: Catalog | None = None) -> Table:
    """Deja la tabla con exactamente los meses pedidos (la recrea si ya existía)."""
    cat = cat or catalogo()
    espacio = config.TABLA.split(".")[0]
    cat.create_namespace_if_not_exists(espacio)
    if cat.table_exists(config.TABLA):
        cat.purge_table(config.TABLA)
    esquema = esquema_iceberg()
    particion = PartitionSpec(PartitionField(source_id=esquema.find_field("inicio").field_id,
                                             field_id=1000, transform=MonthTransform(), name="mes"))
    tabla = cat.create_table(config.TABLA, schema=esquema, partition_spec=particion)
    for mes, ruta in rutas.items():
        datos = normalizar(pq.read_table(ruta, columns=list(config.COLUMNAS)), mes)
        tabla.append(datos)
        print(f"  {mes}: {datos.num_rows:,} viajes")
    return tabla


def abrir(cat: Catalog | None = None) -> Table:
    return (cat or catalogo()).load_table(config.TABLA)
