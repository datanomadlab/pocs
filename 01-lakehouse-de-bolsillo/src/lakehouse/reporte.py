"""Arma docs/resultados.md a partir de las mediciones guardadas en data/."""
from __future__ import annotations

from . import costos


def es(texto: str) -> str:
    """Pasa un número formateado a la inglesa (1,234.5) a formato en español (1.234,5)."""
    return texto.translate(str.maketrans(",.", ".,"))


def _usd(valor: float) -> str:
    if valor == 0:
        return "0"
    if valor < 0.01:
        return es(f"{valor:.6f}".rstrip("0"))
    return es(f"{valor:,.2f}")


def _precio(valor: float) -> str:
    return es(f"{valor:.7f}".rstrip("0").rstrip("."))


def _mb(b: float) -> str:
    return es(f"{b / 1e6:,.1f}") + " MB"


def _ms(segundos: float) -> str:
    return es(f"{segundos * 1000:,.0f}") + " ms"


def _ahorro(base: float, nuevo: float) -> str:
    pct = costos.ahorro_pct(base, nuevo)
    return "no hay costo que ahorrar" if pct is None else f"{pct:.0f} %"


def escenarios(local: dict, esc: dict) -> list[dict]:
    bq, bucket, computo = esc["bigquery"], esc["bucket"], esc["computo"]
    minimo = bq["minimo_bytes_por_tabla"]
    filas = []
    for e in esc["escenario"]:
        f = e["factor_datos"]
        bytes_ejecucion = sum(costos.bytes_facturados(c["bq_bytes_estimados"] * f, minimo)
                              for c in local["consultas"])
        segundos = sum(c["frio_s"] for c in local["consultas"]) * f + computo["arranque_s"]
        fila = {"escenario": e}
        for clave, gratis in (("con_gratis", True), ("sin_gratis", False)):
            fila[clave] = {
                "bq": costos.mensual_bigquery(bytes_ejecucion, e["ejecuciones_dia"],
                                              local["bq_bytes_logicos_total"] * f, bq, gratis),
                "lake": costos.mensual_lakehouse(segundos, e["ejecuciones_dia"],
                                                 local["bodega_bytes"] * f, bucket, computo, gratis)}
        filas.append(fila)
    return filas


def markdown(local: dict, esc: dict, medido_bq: dict | None) -> str:
    bq = esc["bigquery"]
    m = local["maquina"]
    out = ["# Resultados · Experimento 01",
           "",
           "> Archivo generado por `make demo`. No lo edites a mano: vuelve a correr la demo.",
           "",
           f"- **Datos:** NYC TLC, taxis amarillos, meses {', '.join(local['meses'])} "
           f"({es(format(local['filas'], ','))} viajes).",
           f"- **Máquina:** {m['sistema']}, {m['cpu']}, {m['nucleos']} núcleos. DuckDB limitado a "
           f"{local['hilos']} hilos y {local['memoria_gib']} GB para parecerse a un contenedor chico.",
           f"- **Versiones:** DuckDB {local['versiones']['duckdb']}, PyIceberg "
           f"{local['versiones']['pyiceberg']}.",
           f"- **Fecha de la medición:** {local['fecha']}.",
           "",
           "## Por consulta",
           "",
           "DuckDB está **medido** en esta máquina, leyendo la tabla Iceberg desde disco local "
           "(no desde un bucket). BigQuery está **estimado** con las reglas públicas de cobro por "
           "demanda: bytes lógicos de las columnas que toca la consulta."]
    cab = "| Consulta | DuckDB en frío | DuckDB mediana | BigQuery: bytes estimados | BigQuery: USD por corrida |"
    sep = "|---|---|---|---|---|"
    if medido_bq:
        cab += " BigQuery medido: bytes facturados | BigQuery medido: segundos |"
        sep += "---|---|"
    out += ["", cab, sep]
    medidos = {c["nombre"]: c for c in (medido_bq or {}).get("consultas", [])}
    for c in local["consultas"]:
        fact = costos.bytes_facturados(c["bq_bytes_estimados"], bq["minimo_bytes_por_tabla"])
        fila = (f"| {c['descripcion']} | {_ms(c['frio_s'])} | {_ms(c['mediana_s'])} | "
                f"{_mb(c['bq_bytes_estimados'])} | {_usd(costos.costo_bq_consulta(fact, bq['usd_por_tib']))} |")
        if medido_bq:
            r = medidos.get(c["nombre"])
            fila += f" {_mb(r['bytes_facturados'])} | {es(format(r['segundos'], '.2f'))} s |" if r else " sin dato | sin dato |"
        out.append(fila)
    if not medido_bq:
        out += ["", "BigQuery todavía no está medido. Corre `make bq` con una cuenta propia de GCP "
                    "para agregar los bytes facturados y los tiempos reales."]
    out += ["",
            "## Almacenamiento",
            "",
            "| | Tamaño |",
            "|---|---|",
            f"| Parquet de origen (descarga) | {_mb(local['crudos_bytes'])} |",
            f"| Tabla Iceberg (Parquet comprimido + metadatos) | {_mb(local['bodega_bytes'])} |",
            f"| Lo que BigQuery cobraría como almacenamiento lógico (estimado) | "
            f"{_mb(local['bq_bytes_logicos_total'])} |",
            "",
            "## Costo mensual por escenario (modelo)",
            "",
            "Esto es un **modelo**, no una factura. Una ejecución son las 5 consultas una vez. "
            "Los supuestos están en `escenario.toml` y se listan abajo.",
            "",
            "| Escenario | BigQuery (USD/mes) | Lakehouse (USD/mes) | Ahorro | BigQuery sin capa gratuita | "
            "Lakehouse sin capa gratuita | Ahorro sin capa gratuita |",
            "|---|---|---|---|---|---|---|"]
    for f in escenarios(local, esc):
        e, cg, sg = f["escenario"], f["con_gratis"], f["sin_gratis"]
        out.append(f"| **{e['nombre']}**: {e['detalle']} | {_usd(cg['bq'].total)} | {_usd(cg['lake'].total)} | "
                   f"{_ahorro(cg['bq'].total, cg['lake'].total)} | {_usd(sg['bq'].total)} | "
                   f"{_usd(sg['lake'].total)} | {_ahorro(sg['bq'].total, sg['lake'].total)} |")
    c = esc["computo"]
    out += ["",
            "### Supuestos del modelo",
            "",
            f"- Precios (revisar en la fuente antes de publicar): BigQuery por demanda USD {_precio(bq['usd_por_tib'])} "
            f"por TiB, con {bq['tib_gratis_mes']:g} TiB gratis al mes; almacenamiento lógico activo USD "
            f"{_precio(bq['usd_por_gib_mes'])} por GiB al mes, con {bq['gib_gratis_mes']:g} GiB gratis; bucket USD "
            f"{_precio(esc['bucket']['usd_por_gb_mes'])} por GB al mes; contenedor USD {_precio(c['usd_por_vcpu_s'])} por "
            f"vCPU-segundo y USD {_precio(c['usd_por_gib_s'])} por GiB-segundo.",
            f"- El lado lakehouse corre en un contenedor de {c['vcpu']} vCPU y {c['memoria_gib']} GiB que se "
            f"paga solo mientras corre. Cada ejecución suma {c['arranque_s']} s de arranque y latencia del "
            "bucket: ese número es un supuesto, no una medición.",
            "- Los tiempos de DuckDB vienen de un Mac con disco local. Un núcleo de Apple Silicon no es "
            "un vCPU de la nube, y leer de un bucket es más lento que leer de disco.",
            "- Al multiplicar los datos, los bytes escaneados y el tiempo de DuckDB crecen en la misma "
            "proporción. Para 1.000 veces más datos, eso es optimista para un solo nodo.",
            "- No incluye: operaciones ni tráfico de salida del bucket, el costo de mantener la tabla "
            "(compactación, limpieza de snapshots) ni las horas de quien la opera.",
            "- BigQuery se modela por demanda y sin caché: cada ejecución vuelve a escanear, como pasa "
            "cuando los datos cambian entre un refresco y otro. Con caché de resultados, vistas "
            "materializadas o reservas (slots) la cuenta de BigQuery baja.",
            ""]
    return "\n".join(out)
