"""Las siete pruebas de "serio", hechas a los dos caminos con el mismo origen.

Cada prueba devuelve, por camino, un resultado (pasa, pasa con código propio o no pasa) y un detalle
en una frase. La 1 (carga incremental) sale de los días simulados y se arma en medir.py.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from dataclasses import dataclass, field

from . import config, contenedores, destino, origen
from .corte import PUNTOS
from .formato import entero, porcentaje

PASA, CON_CODIGO, NO_PASA = "pasa", "pasa con código propio", "no pasa"


def resultado(pasa: bool, detalle: str, si_pasa: str = PASA) -> dict:
    """`si_pasa` es CON_CODIGO cuando lo que la hace pasar es Python escrito para el experimento,
    no configuración de la herramienta ni SQL."""
    return {"resultado": si_pasa if pasa else NO_PASA, "detalle": detalle}


@dataclass
class Banco:
    """El origen, los días que quedan por simular y todas las corridas hechas, para la prueba 7."""
    con: object
    dias: Iterator[dt.date]
    corridas: list = field(default_factory=list)

    def correr(self, camino: str, corrida: str, corte: str | None = None) -> contenedores.Corrida:
        r = contenedores.correr_job(camino, corrida, corte)
        self.corridas.append(r)
        return r

    def nuevo_dia(self) -> dt.date:
        dia = next(self.dias)
        origen.aplicar(self.con, dia, dia)
        return dia

    def igual(self, camino: str) -> bool:
        return destino.huella(camino) == origen.huella(self.con)


def repetir(b: Banco) -> tuple[dict, dict]:
    """2. Correr dos veces sin cambios en el origen deja las mismas filas."""
    r = {c: b.correr(c, "repetida") for c in config.CAMINOS}
    rastro = destino.rastro("repetida") or {}
    movidas = sum(rastro.get("filas", {}).values())
    total = sum(origen.contar(b.con).values())
    return {
        "dlt": resultado(r["dlt"].codigo == 0 and movidas == 0 and b.igual("dlt"),
                         f"movió {entero(movidas)} filas y el destino quedó igual"),
        "script": resultado(r["script"].codigo == 0 and b.igual("script"),
                            f"volvió a copiar las {entero(total)} y el destino quedó igual"),
    }, {"segundos": r["dlt"].segundos, **rastro}


def _cortar_script(b: Banco, dia: dt.date) -> tuple[bool, float]:
    """docker kill al script mientras escribe lineas.csv, la tabla más grande. Devuelve si se cortó de verdad
    y qué parte de las líneas quedó en el archivo hasta la corrida siguiente."""
    archivo = config.BUCKET / "script" / "lineas.csv"
    antes = archivo.stat().st_mtime_ns if archivo.exists() else 0
    r = contenedores.correr_y_matar("script", f"{dia}-corte",
                                    lambda: archivo.exists() and archivo.stat().st_mtime_ns != antes)
    b.corridas.append(r)
    quedaron = destino.filas("script")["lineas"] / origen.contar(b.con)["lineas"]
    return r.codigo != 0, quedaron


def corte(b: Banco) -> tuple[dict, dict]:
    """3. Se mata la corrida a medio camino; la siguiente termina sin filas repetidas ni faltantes."""
    dlt_ok, script_ok, intactos, quedaron = True, True, 0, []
    for punto in PUNTOS:
        dia = b.nuevo_dia()
        publicada = destino.corrida_publicada()
        r = b.correr("dlt", f"{dia}-corte-{punto}", corte=punto)
        intactos += destino.corrida_publicada() == publicada
        b.correr("dlt", str(dia))
        dlt_ok = dlt_ok and r.codigo != 0 and b.igual("dlt")
        cortado, parte = _cortar_script(b, dia)
        quedaron.append(parte)
        b.correr("script", str(dia))
        script_ok = script_ok and cortado and b.igual("script")
    vistas_sin_registro = destino.filas("dlt")
    solo_registradas = destino.filas_si_solo_cargas_registradas()
    escondidas = sum(vistas_sin_registro[t] - solo_registradas[t] for t in config.TABLAS_ORIGEN)
    n = len(PUNTOS)
    return {
        "dlt": resultado(dlt_ok, f"{n} de {n} cortes: la corrida siguiente dejó el destino igual al origen; "
                                 f"mientras tanto, los reportes de ayer siguieron publicados en {intactos} de {n}"),
        "script": resultado(script_ok, f"se recupera en la corrida siguiente; hasta entonces lineas.csv "
                                       f"quedó con entre {porcentaje(min(quedaron))} y "
                                       f"{porcentaje(max(quedaron))} de las líneas"),
    }, {"filas_escondidas_si_solo_cargas_registradas": escondidas,
        "script_parte_minima": min(quedaron), "script_parte_maxima": max(quedaron)}


def columna_nueva(b: Banco) -> tuple[dict, dict]:
    """4. El origen estrena una columna con valor por defecto: la corrida no se cae y la columna llega con sus
    valores, también en las filas que ya existían."""
    dia = b.nuevo_dia()
    llenadas = origen.agregar_columna(b.con)
    out = {}
    for camino in config.CAMINOS:
        r = b.correr(camino, str(dia))
        llegaron = (destino.uno(destino.conexion(camino), "SELECT count(segmento) FROM clientes")
                    if "segmento" in destino.columnas(camino, "clientes") else 0)
        out[camino] = resultado(r.codigo == 0 and llegaron == llenadas and b.igual(camino),
                                f"la columna llegó con {entero(llegaron)} de sus {entero(llenadas)} valores"
                                + ("" if llegaron == llenadas else ": las filas viejas no cambian de fecha y "
                                   "la carga por fecha de actualización no las vuelve a leer"))
    return out, {"valores": llenadas}


def dato_malo(b: Banco) -> tuple[dict, dict]:
    """5. Un precio negativo detiene la publicación del día y los reportes de ayer siguen disponibles."""
    dia = b.nuevo_dia()
    publicada = destino.corrida_publicada()
    id_linea = origen.meter_dato_malo(b.con, dia)
    rd = b.correr("dlt", str(dia))
    rastro = destino.rastro(str(dia)) or {}
    detuvo = rd.codigo != 0 and rastro.get("resultado") == "detenido" and destino.corrida_publicada() == publicada
    rs = b.correr("script", str(dia))
    copiados = destino.uno(destino.conexion("script"), "SELECT count(*) FROM lineas WHERE precio_unitario < 0")
    origen.arreglar_dato_malo(b.con, id_linea, dia)
    corregida = f"{dia}-corregido"
    for camino in config.CAMINOS:
        b.correr(camino, corregida)
    volvio = destino.corrida_publicada() == corregida and b.igual("dlt")
    return {
        "dlt": resultado(detuvo and volvio, "detuvo la publicación y dejó la de ayer; corregido el dato, la "
                                            "corrida siguiente publicó. Lo hacen 25 líneas de Python del job",
                         si_pasa=CON_CODIGO),
        "script": resultado(copiados == 0, f"copió el precio negativo y terminó bien (código {rs.codigo}): "
                                           "nadie se entera"),
    }, {"pruebas_fallidas": rastro.get("pruebas_fallidas", {})}


def borrado(b: Banco) -> tuple[dict, dict]:
    """6. Una fila que se borra en el origen desaparece del destino."""
    id_linea = origen.borrar_fila(b.con)
    sigue = {}
    for camino in config.CAMINOS:
        b.correr(camino, "borrado")
        sigue[camino] = destino.existe(camino, "lineas", id_linea)
    return {
        "dlt": resultado(not sigue["dlt"], "la línea borrada sigue en el destino: la carga por fecha de "
                                           "actualización no ve lo que ya no está"),
        "script": resultado(not sigue["script"], "la recarga completa la saca"),
    }, {}


def rastro(b: Banco) -> tuple[dict, dict]:
    """7. Cada corrida deja cuántas filas movió, cuánto tardó y cómo terminó; una fallida sale con error."""
    dlt = [c for c in b.corridas if c.camino == "dlt"]
    cortadas = [c for c in dlt if c.codigo == 137]
    con_rastro = [c for c in dlt if c.codigo != 137 and {"filas", "segundos", "resultado"} <= set(
        destino.rastro(c.corrida) or {})]
    fallidas_bien = all((destino.rastro(c.corrida) or {}).get("resultado") == "publicado" or c.codigo != 0
                        for c in con_rastro)
    terminadas = len(dlt) - len(cortadas)
    otros = [a for a in (config.BUCKET / "script").iterdir() if a.suffix != ".csv"]
    return {
        "dlt": resultado(len(con_rastro) == terminadas and fallidas_bien,
                         f"{len(con_rastro)} de {terminadas} corridas terminadas con filas, segundos y "
                         f"resultado; las {len(cortadas)} cortadas salieron con código 137. Lo escribe el job",
                         si_pasa=CON_CODIGO),
        "script": resultado(bool(otros), "no deja nada más que los CSV: ni filas ni tiempos. Cortado, sí sale "
                                         "con error (137)" if not otros else f"dejó {len(otros)} archivos de rastro"),
    }, {"corridas_dlt": len(dlt)}


PRUEBAS = (
    (2, "Repetir no duplica", repetir),
    (3, "Corte a medio camino", corte),
    (4, "Columna nueva en el origen", columna_nueva),
    (5, "Dato malo", dato_malo),
    (6, "Borrado en el origen", borrado),
    (7, "Rastro de cada corrida", rastro),
)
