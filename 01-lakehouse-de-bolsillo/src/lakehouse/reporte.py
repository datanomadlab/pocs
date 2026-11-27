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


MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")


def fecha_larga(iso: str) -> str:
    """2026-11-19 -> 19 de noviembre de 2026."""
    anio, mes, dia = (int(x) for x in iso.split("-"))
    return f"{dia} de {MESES[mes - 1]} de {anio}"


def usd_corto(valor: float) -> str:
    """Dólares para una imagen o un post: sin centavos salvo en montos menores a 1."""
    if valor == 0:
        return "USD 0"
    if valor < 1:
        return "USD " + es(f"{valor:.3f}".rstrip("0"))
    return "USD " + es(f"{valor:,.0f}")


def _toml(valor) -> str:
    if isinstance(valor, list):
        return "[" + ", ".join(_toml(v) for v in valor) + "]"
    return '"' + str(valor).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _bloque(**campos) -> list[str]:
    out = ["[[tabla]]"]
    for clave, valor in campos.items():
        if clave == "filas":
            out.append("filas = [\n" + "".join(f"  {_toml(f)},\n" for f in valor) + "]")
        else:
            out.append(f"{clave} = {_toml(valor)}")
    return out + [""]


def tablas(local: dict, esc: dict, sim: dict | None) -> str:
    """docs/tablas.toml: las tablas del post, redondeadas, para dibujarlas con tools/tabla.py.

    Substack no tiene tablas, así que el post las lleva como imagen. Salen de la misma medición
    que docs/resultados.md para que la imagen nunca quede desfasada.
    """
    simulado = {c["nombre"]: c for c in (sim or {}).get("consultas", [])}

    def igual(nombre: str) -> str:
        c = simulado[nombre]
        if not c["mismo_resultado"]:
            return "distinto"
        dif = c["diferencia_max"] or 0
        return "igual" if dif == 0 else f"igual (±{es(format(dif * 100, '.1f'))} %)"

    columnas = ["Consulta", "DuckDB sobre Iceberg", "BigQuery leería"]
    etiquetas = ["", "medido", "estimado"]
    filas = [[c["descripcion"].replace(" (poda de particiones)", ""), _ms(c["frio_s"]),
              es(f"{c['bq_bytes_estimados'] / 1e6:,.0f}") + " MB"] for c in local["consultas"]]
    total = ["Total", es(f"{sum(c['frio_s'] for c in local['consultas']):.2f}") + " s",
             es(f"{sum(c['bq_bytes_estimados'] for c in local['consultas']) / 1e6:,.0f}") + " MB"]
    if sim:
        columnas.append("SQL de BigQuery")
        etiquetas.append("simulado")
        filas = [f + [igual(c["nombre"])] for f, c in zip(filas, local["consultas"])]
        iguales = sum(simulado[c["nombre"]]["mismo_resultado"] for c in local["consultas"])
        total.append(f"{iguales} de {len(local['consultas'])} iguales")
    m = local["maquina"]
    nota = (f"DuckDB medido el {fecha_larga(local['fecha'])} en {m['cpu']} con disco local, {local['hilos']} hilos y "
            f"{local['memoria_gib']} GB. BigQuery estimado con sus reglas de cobro por demanda.")
    if sim:
        nota += " SQL de BigQuery traducido y corrido sobre la misma tabla, sin cuenta de GCP."
    out = ["# Generado por make demo. No lo edites a mano. Se dibuja con tools/tabla.py.", ""]
    out += _bloque(id="consultas", titulo="Las mismas 5 consultas en los dos caminos", columnas=columnas,
                   etiquetas=etiquetas, filas=filas, total=total, nota=nota)
    out += _bloque(id="escenarios", titulo="Costo mensual por escenario",
                   columnas=["Escenario", "BigQuery", "Lakehouse"], etiquetas=["", "modelo", "modelo"],
                   filas=[[f["escenario"]["detalle"].replace("dashboard que se refresca", "refresco")
                           .replace("los datos medidos", "Los datos medidos")
                           .replace("15 minutos", "15 min"),
                           usd_corto(f["con_gratis"]["bq"].total), usd_corto(f["con_gratis"]["lake"].total)]
                          for f in escenarios(local, esc)],
                   nota="Modelo, no una factura. Una ejecución son las 5 consultas una vez. Precios por demanda "
                        "con capa gratuita; supuestos en escenario.toml.")
    return "\n".join(out)


ANCHO_RESUMEN = 68


def resumen(local: dict, esc: dict, sim: dict | None) -> str:
    """Lo que `make demo` muestra en la terminal: las cifras de las imágenes del post, con su etiqueta.

    Sale de tablas() para que la terminal, las imágenes y el reporte digan lo mismo.
    """
    import tomllib

    t = {x["id"]: x for x in tomllib.loads(tablas(local, esc, sim))["tabla"]}
    total, etiquetas = t["consultas"]["total"], t["consultas"]["etiquetas"]

    def linea(nombre: str, valor: str, etiqueta: str) -> str:
        return f"  {nombre:<22}{valor:<{ANCHO_RESUMEN - 24 - len(etiqueta)}}{etiqueta}"

    n = len(local["consultas"])
    out = [f"Resumen: {es(format(local['filas'], ','))} viajes, {n} consultas por ejecución", "",
           linea("DuckDB sobre Iceberg", f"las {n} en {total[1]}", etiquetas[1]),
           linea("BigQuery leería", f"{total[2]} por ejecución", etiquetas[2])]
    if sim:
        out.append(linea("SQL de BigQuery", total[3], etiquetas[3]))
    def mb(b: float) -> str:
        return es(f"{b / 1e6:,.0f}") + " MB"

    out += [linea("Tabla Iceberg", mb(local["bodega_bytes"]), "medido"),
            linea("BigQuery cobraría", f"{mb(local['bq_bytes_logicos_total'])} lógicos", "estimado"),
            "", f"  {'Costo mensual, modelo':<44}{'BigQuery':>10}{'Lakehouse':>12}"]
    out += [f"  {f[0]:<44}{f[1]:>10}{f[2]:>12}" for f in t["escenarios"]["filas"]]
    return "\n".join(out)


def seccion_simulada(sim: dict, local: dict) -> list[str]:
    estimados = {c["nombre"]: c for c in local["consultas"]}
    out = ["",
           "## BigQuery simulado",
           "",
           f"Esto es una **simulación**, sin cuenta de GCP. Cada `sql/bigquery/*.sql` se leyó con el "
           f"analizador de dialecto BigQuery de sqlglot {sim['sqlglot']}, se tradujo a DuckDB y se corrió "
           "sobre la misma tabla. Comprueba que el SQL es válido, que da lo mismo que la versión DuckDB y "
           "qué columnas y particiones leería BigQuery. **No** mide sus tiempos ni sus bytes facturados.",
           "",
           "| Consulta | SQL válido y mismo resultado | Columnas que lee | Poda particiones | "
           "Bytes según el SQL (simulado) | Coincide con la estimación |",
           "|---|---|---|---|---|---|"]
    for c in sim["consultas"]:
        dif = c["diferencia_max"]
        igual = ("sí" if dif == 0 else f"sí, a {es(format(dif * 100, '.1f'))} %") if c["mismo_resultado"] else "**no**"
        coincide = (c["columnas_coinciden"] and c["poda_coincide"]
                    and c["bytes_simulados"] == estimados[c["nombre"]]["bq_bytes_estimados"])
        out.append(f"| {estimados[c['nombre']]['descripcion']} | {igual} | {', '.join(c['columnas_sql'])} | "
                   f"{'sí' if c['poda_particiones'] else 'no'} | {_mb(c['bytes_simulados'])} | "
                   f"{'sí' if coincide else '**no**'} |")
    out += ["",
            f"La diferencia permitida es {es(format(sim['tolerancia'] * 100, '.0f'))} %: BigQuery calcula los "
            "percentiles con `APPROX_QUANTILES`, que es aproximado, y DuckDB con `quantile_cont`, que es exacto."]
    return out


def markdown(local: dict, esc: dict, medido_bq: dict | None, simulado: dict | None = None) -> str:
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
    if simulado:
        out += seccion_simulada(simulado, local)
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
