"""Las tablas de `make concurrencia`: varias pantallas por cuenta y el costo de enriquecer un evento.

Salen de data/concurrencia.json con la misma forma que las tablas de reporte.py, así van al mismo
docs/resultados.md y al mismo docs/tablas.toml.
"""
from __future__ import annotations

from . import analisis, config
from .formato import O_MAS, decimal, entero, fecha_larga, latencia, por_segundo, segundos

SIN_MEDIR = "sin medir"
NO_TERMINO = "no terminó"
YA_NO_AGUANTABA = "ya no aguantaba"
TRANSPORTES = {"nats": "NATS JetStream", "redpanda": "Redpanda", "kinesis": "Kinesis (emulado)", "sqs": "SQS FIFO (emulado)"}


def _porcentaje(fraccion: float) -> str:
    """Una fracción como porcentaje con un decimal; lo que es exactamente cero se escribe 0."""
    return "0" if fraccion == 0 else decimal(100 * fraccion, 1) + " %"


def faltaron(fase: dict) -> float:
    """Fracción de las entregas esperadas que no llegó a ninguna pantalla."""
    esperadas = fase["entregas_esperadas"]
    return max(esperadas - fase["entregas"], 0) / esperadas if esperadas else 0.0


def techo(resultado: dict | None) -> str:
    """Hasta cuántas entregas por segundo aguantó una combinación."""
    if resultado is None:
        return SIN_MEDIR
    if "nominal" not in resultado:
        return NO_TERMINO
    nominal = resultado["nominal"]
    if not nominal["aguanta"]:
        return _por_que_no(nominal)
    rampa = resultado.get("rampa", [])
    aguantadas = [f for f in rampa if f["aguanta"]]
    completa = len(aguantadas) == len(config.FACTORES_RAMPA)
    # Una rampa que se cortó por un error, sin llegar a un escalón que falle, no encontró el techo.
    if "error" in resultado and not completa and len(aguantadas) == len(rampa):
        return NO_TERMINO
    # Si en el escalón que falló el generador no alcanzó la tasa, el techo queda sin encontrar.
    fallida = next((f for f in rampa if not f["aguanta"]), None)
    sin_techo = completa or (fallida is not None and not analisis.emitio_todo(fallida, fallida["tasa"], fallida["segundos"]))
    mayor = max([resultado["tasa"], *(f["tasa"] for f in aguantadas)]) * resultado["espectadores"]
    return (O_MAS if sin_techo else "") + por_segundo(mayor)


def _por_que_no(fase: dict) -> str:
    """Por qué una fase no aguantó, de lo más básico a lo más fino. Son celdas de una tabla que se
    dibuja como imagen: van cortas y la nota de la tabla las explica."""
    if not analisis.emitio_todo(fase, fase["tasa"], fase["segundos"]):
        return "sin carga"
    falta = faltaron(fase)
    if falta > 0:
        llega = 100 * (1 - falta)
        return f"entrega el {decimal(llega, 0 if llega < 99 else 2)} %"
    if fase["perdidos"] > 0:
        return f"pierde {entero(fase['perdidos'])}"
    return f"p99 de {latencia(fase['latencia_ms']['p99'])}"


def nucleos(resultado: dict | None) -> str:
    """Los núcleos que usó la pieza de entrega con carga nominal."""
    if resultado is None:
        return SIN_MEDIR
    if "nominal" not in resultado:
        return NO_TERMINO
    if not resultado["nominal"]["aguanta"]:
        return "no aguanta"
    usados = resultado["nominal"].get("nucleos")
    return SIN_MEDIR if not usados else decimal(usados["entrega"], 2)


def corte(resultado: dict | None) -> str:
    """Qué parte de las entregas no llegó después de matar la pieza con todas las pantallas conectadas."""
    if resultado is None:
        return SIN_MEDIR
    if "corte" not in resultado:
        return NO_TERMINO
    # Si la pieza ya no entregaba todo antes del corte, lo que falte después no es del corte.
    if not resultado["nominal"]["aguanta"]:
        return YA_NO_AGUANTABA
    falta = faltaron(resultado["corte"])
    # Un porcentaje que redondea a cero no es cero.
    return _porcentaje(falta) if falta == 0 or falta >= 0.0005 else "menos de 0,1 %"


def _peor_congelada(resultados: list[dict]) -> str:
    """El congelamiento más largo entre las combinaciones que aguantaban la carga antes del corte."""
    bajo_techo = [r["corte"]["corte"]["congelada_s"] for r in resultados
                  if "corte" in r and r["nominal"]["aguanta"]]
    if not bajo_techo:
        return ""
    if any(c is None for c in bajo_techo):
        return " Bajo su techo, alguna no volvió antes de que terminara la carga."
    peor = max(bajo_techo)
    # La sonda mide en tramos de 200 ms: sin un tramo vacío, el hueco pudo llegar a casi dos tramos.
    cuanto = "menos de 0,4 s" if peor == 0 else segundos(peor)
    return f" Bajo su techo, la que más tardó en volver a entregar se congeló {cuanto}."


def _escenarios(resultados: list[dict]) -> list[dict]:
    """Los escenarios en el orden en que se midieron, sin repetir."""
    vistos: dict[str, dict] = {}
    for r in resultados:
        vistos.setdefault(r["escenario"], r)
    return list(vistos.values())


def _nombre(escenario: dict) -> str:
    return f"{entero(escenario['pantallas'])} pantallas, {escenario['espectadores']} por cuenta"


def _sin_transporte(cortos: list[str]) -> list[str]:
    """Si todas las rutas comparten transporte («NATS + …»), el encabezado lleva solo la pieza de entrega."""
    prefijos = {c.split(" + ", 1)[0] for c in cortos if " + " in c}
    if len(prefijos) != 1 or not all(" + " in c for c in cortos):
        return cortos
    return [c.split(" + ", 1)[1] for c in cortos]


def _tabla_enriquecer(decorador: list[dict], donde: str) -> dict:
    destinos = sorted({d["destinos"] for d in decorador})
    reglas = sorted({d["reglas"] for d in decorador})
    por_clave = {(d["destinos"], d["reglas"]): d for d in decorador}
    entrada = round(sum(d["bytes_entrada"] for d in decorador) / len(decorador))
    return {
        "id": "enriquecer", "titulo": "Eventos por segundo que enriquece un núcleo",
        "columnas": ["Destinos", *("Sin reglas" if n == 0 else f"{entero(n)} reglas por cuenta" for n in reglas)],
        "etiquetas": ["", *("medido" for _ in reglas)],
        "filas": [[str(n), *(entero(int(round(por_clave[(n, r)]["eventos_s"], -2))) if (n, r) in por_clave else SIN_MEDIR
                             for r in reglas)] for n in destinos],
        "nota": (f"{donde} Un solo hilo en un contenedor limitado a 1 núcleo, con eventos de {entero(entrada)} bytes. "
                 "Por cada evento: lo lee, traduce sus lecturas al nombre y la escala que espera cada destino, evalúa "
                 "las reglas de la cuenta recordando cuáles estaban activas para ese emisor y arma una salida por "
                 "destino. No lee el transporte, no escribe a ningún lado y no comparte el estado con otra réplica."),
    }


def armar_tablas(datos: dict | None) -> list[dict]:
    """Las tablas de concurrencia, o ninguna si `make concurrencia` no se corrió."""
    if not datos:
        return []
    resultados, maq = datos["resultados"], datos["maquina"]
    donde = (f"Medido el {fecha_larga(datos['fecha'])} en {maq['cpu']}, con Docker "
             f"({maq['docker_nucleos']} núcleos y {decimal(maq['docker_memoria_gb'])} GB).")
    tablas = []
    if resultados:
        cortos = {r.id: r for r in config.rutas(todas=True)}
        rutas = list(dict.fromkeys(r["ruta"] for r in resultados))
        escenarios = _escenarios(resultados)
        por_clave = {(r["escenario"], r["ruta"]): r for r in resultados}
        columnas_rutas = _sin_transporte([cortos[r].corto for r in rutas])
        transportes = " y ".join(dict.fromkeys(TRANSPORTES[cortos[r].transporte] for r in rutas))
        cada = round(escenarios[0]["emisores"] / escenarios[0]["tasa"])
        emisores = ", ".join(entero(e["emisores"]) for e in escenarios)
        carga_corte = next((f"en los {r['corte']['segundos']} s de carga" for r in resultados if "corte" in r), "")

        def filas(celda, *antes) -> list[list[str]]:
            return [[_nombre(e), *(f(e) for f in antes), *(celda(por_clave.get((e["escenario"], r))) for r in rutas)]
                    for e in escenarios]

        tablas += [{
            "id": "techo", "titulo": "Varias pantallas por cuenta: hasta dónde aguanta",
            "columnas": ["Escenario", "Entregas/s", *columnas_rutas],
            "etiquetas": ["", "", *("medido" for _ in rutas)],
            "filas": filas(techo, lambda e: entero(e["entregas_s"])),
            "nota": (f"{donde} Transporte {transportes}; una sola instancia de cada pieza de entrega, limitada a 2 "
                     f"núcleos y 2 GB. Eventos de {entero(datos['bytes'])} bytes; cada emisor emite cada {cada} s. "
                     f"Emisores de cada escenario, en orden: {emisores}. "
                     "Entregas/s: eventos por segundo por las pantallas que miran cada cuenta. Cada celda "
                     "es la mayor cantidad de entregas por segundo que aguantó: el generador emite todo, no se pierde "
                     f"nada, el p99 queda bajo {latencia(datos['p99_max_ms'])} y las pantallas reciben al menos el "
                     f"99,9 % de lo esperado. La rampa llega a {config.FACTORES_RAMPA[-1]} veces la carga del escenario. "
                     "«Entrega el N %»: no aguantó ni la carga del escenario, y eso fue lo que alcanzó a entregar."),
        }, {
            "id": "nucleos-concurrencia", "titulo": "Varias pantallas por cuenta: núcleos usados",
            "columnas": ["Escenario", "Entregas/s", *columnas_rutas],
            "etiquetas": ["", "", *("medido" for _ in rutas)],
            "filas": filas(nucleos, lambda e: entero(e["entregas_s"])),
            "nota": ("Núcleos que usó la pieza de entrega con la carga del escenario, de los 2 que tiene. En la ruta "
                     "con Redis no cuentan los de Redis, que corre aparte."),
        }, {
            "id": "corte-concurrencia", "titulo": "Varias pantallas por cuenta: el corte",
            "columnas": ["Escenario", "Entregas/s", *columnas_rutas],
            "etiquetas": ["", "", *("medido" for _ in rutas)],
            "filas": filas(corte, lambda e: entero(e["entregas_s"])),
            "nota": ("Entregas que no llegaron a su pantalla. La pieza de entrega se mata sin aviso a los "
                     f"{config.CORTE_A_LOS} s de carga y se levanta de inmediato; todas las pantallas reconectan a la vez, "
                     "a los 100 ms. Un corte por combinación. El porcentaje es sobre todas las entregas esperadas "
                     f"{carga_corte}, sumando todas las pantallas. «Ya no aguantaba»: la pieza no entregaba todo antes "
                     f"del corte, así que lo que faltó después no es del corte.{_peor_congelada(resultados)}"),
        }]
    if datos.get("decorador"):
        tablas.append(_tabla_enriquecer(datos["decorador"], donde))
    return tablas
