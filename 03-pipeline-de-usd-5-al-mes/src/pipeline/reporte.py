"""Escribe docs/resultados.md, docs/tablas.toml y el resumen de la terminal desde la medición guardada.

Las tres salidas leen la misma medición y el mismo modelo de costos para que la terminal, las imágenes
del post y el reporte digan siempre lo mismo.
"""
from __future__ import annotations

import datetime as dt
import statistics

from . import config, costos
from .formato import entero, fecha_larga, mb, seg, usd

# El resumen se graba en el GIF de la demo: a este ancho se lee en un post sin hacer zoom.
ANCHO_RESUMEN = 68
NOMBRES = {"dlt": "dlt + DuckDB", "script": "Script a mano"}


def linea(nombre: str, valor: str, etiqueta: str) -> str:
    """Una fila del resumen: nombre, valor y la etiqueta pegada al margen derecho."""
    if etiqueta not in config.ETIQUETAS:
        raise ValueError(f"'{nombre}': la etiqueta '{etiqueta}' no es {', '.join(config.ETIQUETAS)}")
    return f"  {nombre:<22}{valor:<{ANCHO_RESUMEN - 24 - len(etiqueta)}}{etiqueta}"


def pasan(medicion: dict, camino: str, resultado: str = "pasa") -> int:
    return sum(p[camino]["resultado"] == resultado for p in medicion["pruebas"])


def conteo(medicion: dict, camino: str) -> str:
    """6 de 7, o 3 de 7 y 2 con código propio."""
    n, con = len(medicion["pruebas"]), pasan(medicion, camino, "pasa con código propio")
    return f"{pasan(medicion, camino)} de {n}" + (f" y {con} con código propio" if con else "")


def cifras(medicion: dict, precios: dict) -> dict:
    """Las cifras que se repiten en las tres salidas, calculadas una sola vez."""
    diarias = medicion["diarias"]
    med = statistics.median
    esc = costos.escenarios(medicion, precios)
    return {
        "dlt_s": med(d["dlt"]["segundos"] for d in diarias), "dlt_peor": max(d["dlt"]["segundos"] for d in diarias),
        "script_s": med(d["script"]["segundos"] for d in diarias),
        "script_peor": max(d["script"]["segundos"] for d in diarias),
        "dlt_filas": med(d["dlt"]["filas"] for d in diarias), "script_filas": med(d["script"]["filas"] for d in diarias),
        "memoria": max(d["dlt"]["memoria_mb"] for d in diarias),
        "escenarios": esc, "base": esc[0], "mayor": esc[-1],
        "fivetran_gratis_hasta": precios["fivetran"]["mar_gratis_mes"] / medicion["volumen_mes"]["filas"],
        "dias_calendario": (dt.date.fromisoformat(medicion["dias"][1])
                            - dt.date.fromisoformat(medicion["dias"][0])).days + 1,
    }


def resumen(medicion: dict, precios: dict) -> str:
    c = cifras(medicion, precios)
    base, mayor = c["base"], c["mayor"]
    fivetran = base["administradas"]
    return "\n".join([
        "Resumen", "",
        linea("Pasa dlt + DuckDB", conteo(medicion, "dlt"), "medido"),
        linea("Pasa el script", conteo(medicion, "script"), "medido"),
        linea("Corrida diaria", f"{seg(c['dlt_s'])} (peor día {seg(c['dlt_peor'])})", "medido"),
        linea("Filas por corrida", f"{entero(round(c['dlt_filas']))} (script {entero(round(c['script_filas']))})",
              "medido"),
        linea("Memoria máxima", f"{entero(round(c['memoria']))} MB de {medicion['limite']['memoria_mb']}", "medido"),
        linea("Nube al mes", f"{usd(base['nuestra']['sin_capa']['total'])} "
                             f"({usd(base['nuestra']['con_capa']['total'])} con capa)", "estimado"),
        linea(f"Con {mayor['factor_datos']} veces más", usd(mayor["nuestra"]["sin_capa"]["total"]), "modelo"),
        linea("Fivetran + BigQuery", f"{usd(fivetran['con_capa']['fivetran'])} plan gratis, "
                                     f"{usd(fivetran['sin_capa']['fivetran'])} pagado", "modelo"),
    ])


def _tabla_pruebas(medicion: dict) -> list[str]:
    out = ["| # | Prueba | dlt + DuckDB | Script a mano |", "|---|---|---|---|"]
    for p in medicion["pruebas"]:
        out.append(f"| {p['id']} | {p['nombre']} | **{p['dlt']['resultado']}**: {p['dlt']['detalle']} "
                   f"| **{p['script']['resultado']}**: {p['script']['detalle']} |")
    return out


def _tabla_corridas(medicion: dict, c: dict) -> list[str]:
    ini, lin, dest = medicion["inicial"], medicion["lineas"], medicion["destino"]
    return [
        "| | dlt + DuckDB | Script a mano |", "|---|---|---|",
        f"| Carga inicial (un año de historia) | {seg(ini['dlt']['segundos'])} | {seg(ini['script']['segundos'])} |",
        f"| Corrida diaria, mediana | {seg(c['dlt_s'])} | {seg(c['script_s'])} |",
        f"| Corrida diaria, peor día | {seg(c['dlt_peor'])} | {seg(c['script_peor'])} |",
        f"| Filas movidas por corrida, mediana | {entero(round(c['dlt_filas']))} | {entero(round(c['script_filas']))} |",
        f"| Memoria máxima, corridas diarias | {entero(round(c['memoria']))} MB de {medicion['limite']['memoria_mb']} "
        "| sin medir |",
        f"| Destino después de los días simulados | {mb(dest['dlt']['bytes'])} en {entero(dest['dlt']['archivos'])} "
        f"archivos | {mb(dest['script']['bytes'])} en {dest['script']['archivos']} archivos |",
        f"| Código que hay que mantener | {lin['dlt']} líneas | {lin['script']} líneas |",
    ]


def _entradas(medicion: dict) -> list[str]:
    q = costos.cantidades(medicion)
    filas = [
        ("Arranque del contenedor y de Python, mediana", seg(q["fijo"])),
        ("Carga de dlt por corrida, mediana", seg(q["carga"])),
        ("Pruebas de datos y reportes por corrida, mediana", seg(q["publicar"])),
        ("Archivos que escribe cada corrida, mediana", entero(round(q["archivos_escritos"]))),
        ("Parquet crudos que lee cada corrida al final del mes", entero(q["archivos_leidos"])),
        ("Destino de dlt al final del mes", mb(q["bytes_bucket"])),
        ("Imagen del job, comprimida", mb(q["bytes_imagen"])),
        ("Filas distintas que cambiaron en los días simulados", entero(q["mar"])),
        ("Lo que pesan esas filas en Postgres", mb(q["bytes_tocados"])),
        ("Lo que pesan las cuatro tablas en Postgres", mb(q["bytes_tablas"])),
    ]
    return ["| Entrada | Valor |", "|---|---|", *(f"| {a} | {b} |" for a, b in filas)]


def _celda(e: dict, lado: str, clave: str) -> str:
    return f"{usd(e[lado]['sin_capa'][clave])} / {usd(e[lado]['con_capa'][clave])}"


def _tabla_costos(c: dict) -> list[str]:
    out = ["| Escenario | dlt + DuckDB en Cloud Run | Fivetran + BigQuery | Airbyte + BigQuery |",
           "|---|---|---|---|"]
    for e in c["escenarios"]:
        out.append(f"| {e['nombre']}: {e['detalle']} | {_celda(e, 'nuestra', 'total')} "
                   f"| {_celda(e, 'administradas', 'fivetran')} | {_celda(e, 'administradas', 'airbyte')} |")
    return out


def _desglose(c: dict) -> list[str]:
    sin, con = c["base"]["nuestra"]["sin_capa"], c["base"]["nuestra"]["con_capa"]
    nombres = {"cloud_run": "Cloud Run (el job)", "scheduler": "Cloud Scheduler (el disparo diario)",
               "bucket": "Cloud Storage (el destino y sus operaciones)", "registro": "Artifact Registry (la imagen)"}
    out = ["| Parte | Sin capa gratuita | Con capa gratuita |", "|---|---|---|"]
    out += [f"| {nombre} | {usd(sin[k])} | {usd(con[k])} |" for k, nombre in nombres.items()]
    return out + [f"| **Total** | **{usd(sin['total'])}** | **{usd(con['total'])}** |"]


def markdown(medicion: dict, precios: dict) -> str:
    c = cifras(medicion, precios)
    m, v, d = medicion["maquina"], medicion["versiones"], medicion["datos"]
    ex = medicion["pruebas_detalle"]
    descartes = "; ".join(f"{k}: {entero(n)}" for k, n in d.items() if k not in ("filas del archivo", "filas que quedan"))
    out = [
        "# Resultados", "", "> Archivo generado por `make demo`. No lo edites a mano: vuelve a correr la demo.", "",
        f"- **Máquina:** {m['sistema']}, {m['cpu']}, {m['nucleos']} núcleos. Cada job corre en un contenedor "
        f"limitado a {medicion['limite']['cpus']} vCPU y {medicion['limite']['memoria_mb']} MB, sin disco propio.",
        f"- **Versiones:** dlt {v['dlt']}, DuckDB {v['duckdb']}, PostgreSQL {v['postgres']}, psycopg2 "
        f"{v['psycopg2-binary']}, PyArrow {v['pyarrow']}, Python {v['python']}, Docker {v['docker']}.",
        f"- **Fecha de la medición:** {medicion['fecha']}.",
        f"- **Datos:** Online Retail II (UCI, CC BY 4.0). {entero(d['filas del archivo'])} líneas en el archivo; "
        f"se descartan {descartes}. Quedan {entero(d['filas que quedan'])}. La historia llega hasta el "
        f"{medicion['historia_hasta']} y se simulan {len(medicion['diarias'])} días con ventas, del "
        f"{medicion['dias'][0]} al {medicion['dias'][1]}.", "",
        "## Las siete pruebas (medido)", "", *_tabla_pruebas(medicion), "",
        f"- Si las vistas leyeran solo las cargas que dlt registró en `_dlt_loads`, el corte entre guardar el "
        f"avance y registrar la carga escondería para siempre {entero(ex['3']['filas_escondidas_si_solo_cargas_registradas'])} "
        "filas: la corrida siguiente cree que ya las cargó.",
        f"- El dato malo lo detectó la prueba {', '.join(ex['5']['pruebas_fallidas']) or 'ninguna'}.", "",
        "## Las corridas (medido)", "", *_tabla_corridas(medicion, c), "",
        f"Los reportes son {medicion['lineas']['n_reportes']} consultas SQL ({medicion['lineas']['reportes']} líneas) "
        "que corren solo en el camino de dlt; el script no los tiene. Las líneas no cuentan vacías ni comentarios, "
        "ni el Dockerfile, que es el mismo para los dos, ni la configuración del despliegue (job, programador, "
        "permisos y clave de la base), que todavía no existe.", "",
        "## Costo mensual", "",
        "Cada celda: sin capa gratuita / con capa gratuita. La primera fila de la primera columna es **estimada** "
        "(segundos medidos por precios publicados); el resto es **modelo**.", "",
        *_tabla_costos(c), "",
        f"Desglose de la primera fila: {seg(c['base']['nuestra']['sin_capa']['segundos'])} por corrida más "
        f"{precios['cloud_run']['arranque_s']} s de arranque, cobrados como un minuto:", "", *_desglose(c), "",
        f"- Con {c['mayor']['factor_datos']} veces más ventas la corrida duraría "
        f"{seg(c['mayor']['nuestra']['sin_capa']['segundos'])} y seguiría lejos de USD "
        f"{precios['modelo']['umbral_usd_mes']}. Lo que no está medido es si cabe en 512 MB: el costo no es lo "
        "primero que se rompe.",
        f"- Fivetran deja el plan gratuito desde {entero(round(c['fivetran_gratis_hasta']))} veces los datos medidos: "
        f"{entero(medicion['volumen_mes']['filas'])} filas activas en los {len(medicion['diarias'])} días con ventas "
        f"simulados (medido en el origen). Esos días ocupan {c['dias_calendario']} días de calendario, así que la "
        "cifra sobrestima un mes.", "",
        "## Entradas del modelo (medido)", "",
        "Lo que el modelo toma de la medición, para rehacer la cuenta con otros precios:", "",
        *_entradas(medicion), "",
        "## Supuestos", "",
        "- **El más fuerte:** cargar y publicar crecen en proporción a los datos y la corrida sigue cabiendo en "
        "1 vCPU y 512 MB. Con los datos medidos usa "
        f"{entero(round(c['memoria']))} MB; con 10 o 100 veces más no está medido.",
        "- El job llega a Postgres por internet, con usuario y clave. Si la base solo acepta direcciones conocidas, "
        "hace falta una IP de salida fija para Cloud Run, que no está en el modelo y puede costar más que todo lo demás.",
        "- El bucket se monta como carpeta del contenedor (Cloud Storage FUSE), sin costo aparte. No está probado.",
        "- Los montos son infraestructura: no incluyen las horas de quien opera, ni alertas.",
        f"- Cloud Run tarda {precios['cloud_run']['arranque_s']} s en partir el contenedor (no medido). Con un "
        "minuto mínimo por corrida, cambia poco.",
        "- Fivetran cobra las filas distintas que cambiaron en el mes; Airbyte, el volumen serializado, que aquí se "
        f"supone {precios['airbyte']['factor_volumen']} veces lo que pesan en Postgres.",
        "- BigQuery almacena lo que pesan las tablas en Postgres y cada reporte lee las tablas completas.",
        "- Precios de lista en us-central1, revisados el "
        f"{fecha_larga(precios['cloud_run']['revisado'])}. Todo está en `escenario.toml`.",
    ]
    return "\n".join(out) + "\n"


def _toml(texto: str) -> str:
    return '"' + str(texto).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _fila(*celdas: str) -> str:
    return "  [" + ", ".join(_toml(x) for x in celdas) + "],\n"


def tablas(medicion: dict, precios: dict) -> str:
    """docs/tablas.toml: las tablas del post (Substack no tiene tablas), que dibuja `make tablas`."""
    c = cifras(medicion, precios)
    pruebas = "".join(_fila(p["nombre"], p["dlt"]["resultado"], p["script"]["resultado"]) for p in medicion["pruebas"])
    esc = "".join(_fila(e["nombre"], _celda(e, "nuestra", "total"), _celda(e, "administradas", "fivetran"),
                        _celda(e, "administradas", "airbyte")) for e in c["escenarios"])
    fecha = fecha_larga(medicion["fecha"])
    nota_pruebas = (f"Medido el {fecha}, con cada job limitado a 1 vCPU y 512 MB. {len(medicion['diarias'])} días "
                    "con ventas y las pruebas sobre el mismo origen Postgres.")
    nota_costos = ("Modelo con precios de lista en us-central1 y una corrida al día. La primera fila de dlt + DuckDB "
                   f"es estimada con los segundos medidos ({seg(c['dlt_s'])} por corrida). Airbyte no tiene plan "
                   "gratuito. Supuestos en escenario.toml.")
    return (
        "# Generado por make demo. No lo edites a mano.\n\n"
        "[[tabla]]\nid = \"pruebas\"\ntitulo = \"Las siete pruebas de un ELT serio\"\n"
        "columnas = [\"Prueba\", \"dlt + DuckDB\", \"Script a mano\"]\netiquetas = [\"\", \"medido\", \"medido\"]\n"
        f"filas = [\n{pruebas}]\n"
        f"total = [\"Pasan\", {_toml(conteo(medicion, 'dlt'))}, {_toml(conteo(medicion, 'script'))}]\n"
        f"nota = {_toml(nota_pruebas)}\n\n"
        "[[tabla]]\nid = \"costos\"\ntitulo = \"Costo mensual, sin capa gratuita / con capa gratuita\"\n"
        "columnas = [\"Escenario\", \"dlt + DuckDB\", \"Fivetran + BigQuery\", \"Airbyte + BigQuery\"]\n"
        "etiquetas = [\"\", \"modelo\", \"modelo\", \"modelo\"]\n"
        f"filas = [\n{esc}]\n"
        f"nota = {_toml(nota_costos)}\n"
    )
