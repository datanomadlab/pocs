"""Escribe docs/resultados.md, docs/tablas.toml y el resumen de la terminal desde la medición guardada.

Las tres salidas leen la misma medición para que la terminal, las imágenes del post y el reporte
digan siempre lo mismo. Cada celda sale de una de las funciones de abajo, que las tres comparten.
"""
from __future__ import annotations

from . import analisis, config
from .formato import decimal, entero, fecha_larga, latencia, por_segundo, segundos, usd_corto

# El resumen se graba en el GIF de la demo: a este ancho se lee en un post sin hacer zoom.
ANCHO_RESUMEN = 68
SIN_MEDIR = "sin medir"


def _validar(medicion: dict) -> list[dict]:
    for r in medicion["rutas"]:
        if r["etiqueta"] not in config.ETIQUETAS:
            raise ValueError(f"'{r['id']}': la etiqueta '{r['etiqueta']}' no es {', '.join(config.ETIQUETAS)}")
    return medicion["rutas"]


# --- Celdas: una función por dato, para que todas las salidas lo escriban igual ----------------

def p99(ruta: dict) -> str:
    return latencia(ruta["nominal"]["latencia_ms"]["p99"]) if "nominal" in ruta else SIN_MEDIR


def aguanta(ruta: dict) -> str:
    rampa = ruta.get("rampa")
    if rampa is None:
        return SIN_MEDIR
    if rampa["aguanta_hasta"] == 0:
        return "no cumple"
    return ("≥ " if rampa["llego_al_tope"] else "") + por_segundo(rampa["aguanta_hasta"])


def nucleos(ruta: dict) -> str:
    n = ruta.get("nominal", {}).get("nucleos")
    return f"{decimal(n['transporte'], 2)} + {decimal(n['entrega'], 2)}" if n else SIN_MEDIR


def codigo(ruta: dict) -> str:
    if ruta["lineas_codigo"]:
        return f"{ruta['lineas_codigo']} líneas"
    return f"{ruta['lineas_configuracion']} de config."


def orden(ruta: dict) -> str:
    """Qué llegó a la pantalla con carga estable."""
    fase = ruta.get("nominal")
    if fase is None:
        return SIN_MEDIR
    problemas = [f"{entero(fase[k])} {texto}" for k, texto in
                 (("perdidos", "perdidos"), ("duplicados", "repetidos"), ("desordenados", "fuera de orden")) if fase[k]]
    return ", ".join(problemas) or "sin fallas"


def _corte(ruta: dict) -> dict | None:
    """El peor valor de cada columna entre los cortes de la ruta."""
    return analisis.peor_por_columna(ruta["cortes"]) if ruta.get("cortes") else None


def congelada(ruta: dict) -> str:
    fase = _corte(ruta)
    if fase is None:
        return SIN_MEDIR
    valor = fase["corte"]["congelada_s"]
    if valor is None:
        return "no volvió"
    # La sonda mide en tramos de 200 ms: sin un tramo vacío, el hueco pudo llegar a casi dos tramos.
    return "< 0,4 s" if valor == 0 else segundos(valor)


def atraso_maximo(ruta: dict) -> str:
    """El evento que más tardó en llegar a la pantalla después del corte."""
    fase = _corte(ruta)
    return SIN_MEDIR if fase is None else segundos(fase["corte"]["atraso_max_s"])


def no_llegaron(ruta: dict) -> str:
    fase = _corte(ruta)
    return SIN_MEDIR if fase is None else entero(fase["perdidos"])


def repetidos(ruta: dict) -> str:
    fase = _corte(ruta)
    return SIN_MEDIR if fase is None else entero(fase["duplicados"])


def fuera_de_orden(ruta: dict) -> str:
    fase = _corte(ruta)
    return SIN_MEDIR if fase is None else entero(fase["desordenados"])


def horas(valor: float) -> str:
    if abs(valor) < 0.05:
        return "igual"
    return ("+" if valor > 0 else "−") + decimal(abs(valor), 1) + " h"


# --- Tablas: las mismas filas van al markdown y a tablas.toml ----------------------------------

def _escenario_medido(medicion: dict) -> dict:
    """El escenario de costos que coincide con la tasa medida; si no hay, el primero."""
    escenarios = medicion["costos"]["escenarios"]
    return next((e for e in escenarios if e["eventos_s"] == medicion["parametros"]["tasa"]), escenarios[0])


def _nota_sin_comprimir() -> str:
    """Las rutas donde el productor de Kafka escribe sin comprimir, para que la tabla lo diga."""
    rutas = [r.corto for r in config.rutas(todas=True) if r.sin_comprimir]
    return f" En {' y '.join(rutas)} el productor escribe a Kafka sin comprimir." if rutas else ""


def armar_tablas(medicion: dict) -> list[dict]:
    rutas = _validar(medicion)
    p = medicion["parametros"]
    medidas = [r for r in rutas if r["etiqueta"] == "medido"]
    simuladas = [r for r in rutas if r["etiqueta"] == "simulado"]
    donde = (f"Medido el {fecha_larga(medicion['fecha'])} en {medicion['maquina']['cpu']}, con Docker, "
             f"cada pieza limitada a 2 núcleos y 2 GB.")
    tablas = []
    if medidas:
        tablas.append({
            "id": "pantalla", "titulo": f"Lo que ve la pantalla a {por_segundo(p['tasa'])}",
            "columnas": ["Ruta", "p99 en pantalla", "Aguanta hasta", "Núcleos", "Código propio"],
            "etiquetas": ["", "medido", "medido", "medido", "medido"],
            "filas": [[r["corto"], p99(r), aguanta(r), nucleos(r), codigo(r)] for r in medidas],
            "nota": (f"{donde} {entero(p['emisores'])} emisores, {entero(p['pantallas'])} pantallas, eventos de "
                     f"{p['bytes']} bytes. Aguanta: la mayor tasa con p99 bajo {latencia(p['p99_max_ms'])} y sin pérdida; "
                     f"la rampa llega hasta {por_segundo(p['tasa'] * config.FACTORES_RAMPA[-1])}. Núcleos: los que usó el "
                     "transporte más los que usó la entrega; en la ruta con Redis no cuentan los de Redis, que "
                     "corre aparte con 1 núcleo. Código propio: líneas que el equipo escribe y mantiene; "
                     "en Centrifugo, Zilla y EMQX son líneas de configuración. «6 s» es el tiempo de sesión del grupo "
                     "de Kafka; de fábrica son 45 s en Go y 30 s en Node." + _nota_sin_comprimir())})
        tablas.append({
            "id": "corte", "titulo": "Al matar la pieza que entrega a las pantallas",
            "columnas": ["Ruta", "Congelada", "Atraso máx.", "No llegaron", "Repetidos", "Sin orden"],
            "etiquetas": ["", "medido", "medido", "medido", "medido", "medido"],
            "filas": [[r["corto"], congelada(r), atraso_maximo(r), no_llegaron(r), repetidos(r), fuera_de_orden(r)] for r in medidas],
            "nota": (f"La pieza se mata sin aviso a los {config.CORTE_A_LOS} s de carga y se levanta de inmediato. "
                     f"Se repite {p['cortes']} veces por ruta y cada columna muestra su peor valor. Congelada: tiempo sin "
                     "que llegue nada a la pantalla. Atraso máx.: lo que tardó en llegar el evento más demorado. Sin orden: "
                     "eventos que llegaron después de uno posterior del mismo emisor; como cada emisor emite cada "
                     f"{entero(p['emisores'] // p['tasa'])} s, solo se ve un desorden mayor que eso. Las pantallas se "
                     "reconectan a los 100 ms. "
                     f"No llegaron: eventos que ninguna pantalla recibió hasta {config.MARGEN_CORTE} s después de terminar la carga.")})
    if simuladas:
        tablas.append({
            "id": "simuladas", "titulo": "Las rutas sobre servicios de AWS, contra emuladores",
            "columnas": ["Ruta", "Tasa", "Congelada", "Atraso máx.", "No llegaron", "Código propio"],
            "etiquetas": ["", "simulado", "simulado", "simulado", "simulado", "medido"],
            "filas": [[r["corto"], por_segundo(r["tasa"]), congelada(r), atraso_maximo(r), no_llegaron(r), codigo(r)]
                      for r in simuladas],
            "nota": (_estable(simuladas) + " Kinesis y SQS son emuladores locales: comprueban que la ruta "
                     f"funciona y qué hace el código frente a un corte (el peor valor de {p['cortes']}). No dicen cuánto tarda ni cuánto aguanta el servicio real.")})
    costos = medicion.get("costos")
    if costos:
        escenarios = costos["escenarios"]
        ids = [c["id"] for c in escenarios[0]["caminos"]]
        por_id = [{c["id"]: c for c in e["caminos"]} for e in escenarios]
        tablas.append({
            "id": "costos", "titulo": "Costo mensual de cada camino",
            "columnas": ["Camino"] + [f"{entero(e['eventos_s'])} eventos/s" for e in escenarios],
            "etiquetas": [""] + ["modelo"] * len(escenarios),
            "filas": [[por_id[0][i]["nombre"]] + [usd_corto(e[i]["usd_total"]) for e in por_id] for i in ids],
            "nota": ("Modelo, no una factura: precios por demanda de us-east-1 y supuestos en escenario.toml. "
                     "Flink: administrado, una aplicación por consumidor. Propio: un consumidor escrito a mano. SQS FIFO: "
                     "con SNS FIFO repartiendo a 3 colas; empaquetado lleva 10 eventos por mensaje y pide consumidor "
                     "propio. MSK: Kafka administrado. Redpanda y NATS: 3 nodos propios. "
                     "Incluye transporte, transferencia entre zonas y el cómputo de la entrega para 3 consumidores. "
                     "La línea base lleva además la pieza que habla WebSocket. No incluye el disco de los brokers "
                     "propios, Redis para Centrifugo, la salida a internet hacia las pantallas, el balanceador ni "
                     "horas de personas. "
                     + _nota_flink(escenarios[-1]))})
        medido = _escenario_medido(medicion)
        valores = sorted(int(v) for v in medido["caminos"][0]["equilibrio_h"])
        base = next(c for c in medido["caminos"] if c["id"] == costos["base"])
        tablas.append({
            "id": "equilibrio", "titulo": "Cuántas horas caídas al mes vale la diferencia",
            "columnas": ["Camino", "Diferencia"] + [f"Hora a {usd_corto(v)}" for v in valores],
            "etiquetas": ["", "modelo"] + ["modelo"] * len(valores),
            "filas": [[c["nombre"], _diferencia(c["usd_total"] - base["usd_total"])]
                      + [horas(c["equilibrio_h"][str(v)]) for v in valores]
                      for c in medido["caminos"] if c["id"] != costos["base"]],
            "nota": (f"A {medido['detalle']}, contra la línea base, {base['nombre']} ({usd_corto(base['usd_total'])} "
                     "al mes). Cada columna supone un costo distinto de la hora caída. Con signo +, el "
                     "camino es más caro: conviene solo si evita al menos esas horas de caída al mes. Con signo −, es "
                     "más barato: sigue conviniendo aunque sume hasta esas horas.")})
    return tablas


def _estable(rutas: list[dict]) -> str:
    """Qué pasó con carga estable, antes de cualquier corte."""
    con_fallas = [f"{r['corto']}: {orden(r)}" for r in rutas if orden(r) not in ("sin fallas", SIN_MEDIR)]
    if con_fallas:
        return "Con carga estable hubo fallas: " + "; ".join(con_fallas) + "."
    return ("Con carga estable, todas entregaron todo. El orden no se pudo comprobar: a estas tasas cada emisor "
            "emite a lo más una vez por corrida.")


def _nota_flink(escenario: dict) -> str:
    """Cuánto pesa el supuesto de capacidad de Flink, que no se midió."""
    f = escenario["flink"]
    return (f"Flink no se midió: su costo supone 1 MB por segundo por KPU. A {escenario['detalle']}, las aplicaciones de "
            f"Flink cuestan {usd_corto(f['supuesto'])}; {usd_corto(f['mitad'])} si una KPU rinde la mitad y "
            f"{usd_corto(f['doble'])} si rinde el doble.")


def _diferencia(usd: float) -> str:
    if abs(usd) < 0.5:
        return "USD 0"
    return ("+" if usd > 0 else "−") + usd_corto(abs(usd))


def _toml(texto: str) -> str:
    return '"' + str(texto).replace("\\", "\\\\").replace('"', '\\"') + '"'


def tablas(medicion: dict) -> str:
    """docs/tablas.toml: las tablas del post (Substack no tiene tablas), que dibuja `make tablas`."""
    out = ["# Generado por make demo. No lo edites a mano. Se dibuja con tools/tabla.py.", ""]
    for t in armar_tablas(medicion):
        out += ["[[tabla]]", f"id = {_toml(t['id'])}", f"titulo = {_toml(t['titulo'])}",
                "columnas = [" + ", ".join(_toml(c) for c in t["columnas"]) + "]",
                "etiquetas = [" + ", ".join(_toml(c) for c in t["etiquetas"]) + "]", "filas = ["]
        out += ["  [" + ", ".join(_toml(c) for c in fila) + "]," for fila in t["filas"]]
        out += ["]", f"nota = {_toml(t['nota'])}", ""]
    return "\n".join(out)


def markdown(medicion: dict) -> str:
    maq, p = medicion["maquina"], medicion["parametros"]
    out = ["# Resultados", "",
           "> Archivo generado por `make demo`. No lo edites a mano: vuelve a correr la demo.", "",
           f"- **Máquina:** {maq['sistema']}, {maq['cpu']}, {maq['nucleos']} núcleos. "
           f"Docker {maq['docker']} con {maq['docker_nucleos']} núcleos y {decimal(maq['docker_memoria_gb'])} GB.",
           f"- **Fecha de la medición:** {medicion['fecha']}.",
           f"- **Carga:** {por_segundo(p['tasa'])} (menos en las rutas simuladas: ver su tabla), "
           f"{entero(p['emisores'])} emisores en {entero(p['cuentas'])} cuentas, {entero(p['pantallas'])} pantallas, "
           f"eventos de {p['bytes']} bytes.",
           "- **Versiones:** " + ", ".join(f"{k} {v}" for k, v in medicion["versiones"].items()) + ".",
           "- **Etiquetas:** medido (corrió en esta máquina), simulado (contra un emulador: comprueba que funciona, "
           "no cuánto tarda ni cuánto cobra) y modelo (proyección con los supuestos de `escenario.toml`).", ""]
    if medicion.get("rapido"):
        out += ["> **Corrida rápida (RAPIDO=1):** fases acortadas para probar que todo levanta. Estas cifras no se publican.", ""]
    for t in armar_tablas(medicion):
        encabezado = [c + (f" ({e})" if e else "") for c, e in zip(t["columnas"], t["etiquetas"])]
        out += [f"## {t['titulo']}", "", "| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
        out += ["| " + " | ".join(fila) + " |" for fila in t["filas"]]
        out += ["", t["nota"], ""]
    fallidas = [r for r in medicion["rutas"] if "error" in r]
    if fallidas:
        out += ["## Rutas que no terminaron", ""] + [f"- **{r['nombre']}:** {r['error']}" for r in fallidas] + [""]
    return "\n".join(out)


def costos_markdown(medicion: dict) -> str:
    """Solo las tablas de costos, para el escenario propio que no se publica."""
    out = ["# Costos con escenario.local.toml", ""]
    for t in armar_tablas(medicion):
        if t["id"] not in ("costos", "equilibrio"):
            continue
        out += [f"## {t['titulo']}", "", "| " + " | ".join(t["columnas"]) + " |", "|" + "---|" * len(t["columnas"])]
        out += ["| " + " | ".join(fila) + " |" for fila in t["filas"]] + ["", t["nota"], ""]
    return "\n".join(out)


def resumen(medicion: dict) -> str:
    """Lo que se ve al final de make demo y en la demo animada: una línea por ruta y los costos."""
    rutas = _validar(medicion)
    if not rutas:
        return "Resumen: todavía no hay rutas medidas"
    p = medicion["parametros"]

    def fila(nombre: str, a: str, b: str, c: str, d: str, etiqueta: str) -> str:
        cuerpo = f"{nombre:<{config.LARGO_CORTO + 1}}{a:<7}{b:<11}{c:<10}{d}"
        return f"{cuerpo:<{ANCHO_RESUMEN - len(etiqueta)}}{etiqueta}".rstrip()

    out = [f"Resumen · {por_segundo(p['tasa'])}, {entero(p['pantallas'])} pantallas, 2 núcleos por pieza", "",
           fila("", "", "", "al matar la entrega", "", ""),
           fila("Ruta", "p99", "aguanta", "congela", "pierde", "")]
    for r in rutas:
        if "nominal" not in r:
            out.append(fila(r["corto"], "no terminó", "", "", "", r["etiqueta"]))
            continue
        if not r.get("cortes"):
            out.append(fila(r["corto"], p99(r), "—", "no terminó", "", r["etiqueta"]))
            continue
        out.append(fila(r["corto"], p99(r), aguanta(r) if "rampa" in r else "—", congelada(r), no_llegaron(r),
                        r["etiqueta"]))
    if medicion.get("costos"):
        medido = _escenario_medido(medicion)
        titulo = f"Costo al mes, {medido['detalle']}"
        out += ["", f"{titulo:<{ANCHO_RESUMEN - 6}}modelo"]
        out += [f"  {c['nombre']:<42}{usd_corto(c['usd_total'])}" for c in medido["caminos"]]
    return "\n".join(out)
