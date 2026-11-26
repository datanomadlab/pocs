"""Modelo de costo mensual de cada camino. Funciones puras: precios y supuestos entran por parámetro.

Los precios y supuestos viven en escenario.toml. Lo único que viene de la medición son los núcleos
que usó cada pieza a la tasa medida; el resto es cómo cobra cada servicio.
"""
from __future__ import annotations

import math

BASE = "kinesis-flink"  # la línea base: contra este camino se calcula el punto de equilibrio


def volumen(eventos_s: float, carga: dict) -> tuple[float, float]:
    """Eventos y GB (decimales) al mes."""
    eventos = eventos_s * 3600 * carga["horas_mes"]
    return eventos, eventos * carga["bytes_por_evento"] / 1e9


def kinesis(eventos_s: float, carga: dict, k: dict, lectores: int | None = None) -> dict:
    """Kinesis aprovisionado: shards, unidades de escritura y, si aplica, enhanced fan-out por lector.

    lectores: procesos que leen el stream completo, cada uno registrado como consumidor de fan-out.
    Por defecto, uno por consumidor."""
    lectores = carga["consumidores"] if lectores is None else lectores
    eventos, gb = volumen(eventos_s, carga)
    por_registros = eventos_s / k["registros_s_por_shard"]
    por_bytes = eventos_s * carga["bytes_por_evento"] / k["bytes_s_por_shard"]
    shards = math.ceil(max(por_registros, por_bytes) / k["llenado_shard"])
    unidades = eventos * math.ceil(carga["bytes_por_evento"] / k["bytes_unidad_put"])
    usd = shards * k["usd_shard_hora"] * carga["horas_mes"] + unidades / 1e6 * k["usd_millon_unidades_put"]
    if k["fan_out"]:
        usd += lectores * (shards * k["usd_consumidor_shard_hora"] * carga["horas_mes"] + gb * k["usd_gb_fan_out"])
    return {"shards": shards, "usd": usd}


def flink(eventos_s: float, carga: dict, f: dict, factor_capacidad: float = 1.0) -> dict:
    """Flink administrado: una aplicación por consumidor. La KPU de orquestación paga horas pero no disco."""
    mb_s = eventos_s * carga["bytes_por_evento"] / 1e6
    proceso = math.ceil(mb_s / (f["mb_s_por_kpu"] * factor_capacidad))
    kpu = proceso + f["kpu_orquestacion"]
    por_aplicacion = (kpu * f["usd_kpu_hora"] * carga["horas_mes"]
                      + proceso * f["gb_disco_por_kpu"] * f["usd_gb_mes_disco"])
    return {"kpu_por_aplicacion": kpu, "usd": carga["consumidores"] * por_aplicacion}


def _nucleos_necesarios(nucleos_medidos: float, tasa_medida: float, eventos_s: float, carga: dict) -> float:
    return nucleos_medidos * eventos_s / tasa_medida / carga["utilizacion"]


def fargate(nucleos_medidos: float, tasa_medida: float, eventos_s: float, carga: dict, fg: dict) -> dict:
    """Piezas de entrega en Fargate: réplicas por consumidor, cada una en el tamaño que alcance."""
    necesita = _nucleos_necesarios(nucleos_medidos, tasa_medida, eventos_s, carga)
    mayor = fg["tamanos_vcpu"][-1]
    tareas = max(math.ceil(necesita / mayor), 1)
    vcpu = next(t for t in fg["tamanos_vcpu"] if t >= necesita / tareas)
    gb = max(vcpu * fg["gb_por_vcpu"], 1)
    por_tarea = (vcpu * fg["usd_vcpu_hora"] + gb * fg["usd_gb_hora"]) * carga["horas_mes"]
    cantidad = tareas * carga["replicas_entrega"] * carga["consumidores"]
    return {"vcpu": vcpu, "tareas": cantidad, "usd": cantidad * por_tarea}


def _transferencia_clientes(gb: float, carga: dict, tr: dict) -> float:
    """Lo que cruza de zona entre el productor, los consumidores y los brokers. Se cobra a ambos lados."""
    flujos = 1 + carga["consumidores"]
    return flujos * gb * tr["fraccion_entre_zonas"] * tr["usd_gb_entre_zonas"] * 2


def brokers_propios(nucleos_medidos: float, tasa_medida: float, eventos_s: float, carga: dict,
                    ec2: dict, tr: dict) -> dict:
    """Brokers en instancias propias, uno por zona con replicación 3. El disco no está modelado."""
    _, gb = volumen(eventos_s, carga)
    necesita = _nucleos_necesarios(nucleos_medidos, tasa_medida, eventos_s, carga)
    mayor = ec2["vcpu_por_nodo"][-1]
    grupos = max(math.ceil(necesita / mayor), 1)
    tipo = next(i for i, v in enumerate(ec2["vcpu_por_nodo"]) if v >= necesita / grupos)
    nodos = ec2["nodos_minimos"] * grupos
    replicacion = (ec2["nodos_minimos"] - 1) * gb * tr["usd_gb_entre_zonas"] * 2
    return {"nodos": nodos, "vcpu_por_nodo": ec2["vcpu_por_nodo"][tipo],
            "usd": nodos * ec2["usd_hora_por_nodo"][tipo] * carga["horas_mes"],
            "usd_transferencia": replicacion + _transferencia_clientes(gb, carga, tr)}


def msk(eventos_s: float, carga: dict, m: dict, tr: dict) -> dict:
    """Kafka administrado (MSK Express): AWS opera los brokers y no cobra la replicación."""
    _, gb = volumen(eventos_s, carga)
    mb_s = eventos_s * carga["bytes_por_evento"] / 1e6
    por_entrada = mb_s / m["mb_s_entrada_por_broker"]
    por_salida = mb_s * carga["consumidores"] / m["mb_s_salida_por_broker"]
    necesita = math.ceil(max(por_entrada, por_salida) / carga["utilizacion"])
    minimo = m["brokers_minimos"]
    brokers = max(minimo, math.ceil(necesita / minimo) * minimo)   # la misma cantidad en cada zona
    retenido_gb = mb_s * 3600 * m["horas_retencion"] / 1000
    usd = (brokers * m["usd_broker_hora"] * carga["horas_mes"] + gb * m["usd_gb_entrada"]
           + retenido_gb * m["usd_gb_mes_disco"])
    return {"brokers": brokers, "usd": usd, "usd_transferencia": _transferencia_clientes(gb, carga, tr)}


def sns_sqs(eventos_s: float, carga: dict, sns: dict, sqs: dict, eventos_por_mensaje: int = 1) -> dict:
    """Un tema SNS FIFO que reparte a una cola SQS FIFO por consumidor. Todo se cobra por solicitud."""
    eventos, gb = volumen(eventos_s, carga)
    mensajes = eventos / eventos_por_mensaje
    bytes_lote = sqs["mensajes_por_lote"] * carga["bytes_por_evento"] * eventos_por_mensaje
    trozos = math.ceil(bytes_lote / sqs["bytes_por_solicitud"])
    lotes = mensajes / sqs["mensajes_por_lote"]
    consumidores = carga["consumidores"]
    usd_sns = (lotes * trozos / 1e6 * sns["usd_millon_publicaciones"] + gb * sns["usd_gb_publicado"]
               + mensajes * consumidores / 1e6 * sns["usd_millon_entregas"] + gb * consumidores * sns["usd_gb_entregado"])
    usd_sqs = consumidores * lotes * sqs["solicitudes_por_lote"] * trozos / 1e6 * sqs["usd_millon_solicitudes"]
    return {"usd_sns": usd_sns, "usd_sqs": usd_sqs, "usd": usd_sns + usd_sqs}


def caminos(eventos_s: float, e: dict, medidos: dict) -> list[dict]:
    """El costo mensual de cada camino a un volumen dado.

    medidos: {"tasa": eventos/s de la medición, "entrega": {pieza: núcleos}, "transporte": {nombre: núcleos}}.
    Un camino cuya pieza no se midió queda fuera, en vez de entrar con un número inventado.
    """
    carga, tr, tasa = e["carga"], e["transferencia"], medidos["tasa"]

    def entrega(pieza: str) -> dict | None:
        nucleos = medidos["entrega"].get(pieza)
        return None if nucleos is None else fargate(nucleos, tasa, eventos_s, carga, e["fargate"])

    def propio(transporte: str) -> dict | None:
        nucleos = medidos["transporte"].get(transporte)
        return None if nucleos is None else brokers_propios(nucleos, tasa, eventos_s, carga, e["ec2"], tr)

    k = kinesis(eventos_s, carga, e["kinesis"])
    # Cada réplica de un consumidor propio lee el stream completo: las pantallas de una réplica
    # necesitan todos los eventos, así que no pueden repartirse los shards entre réplicas.
    k_propio = kinesis(eventos_s, carga, e["kinesis"], carga["consumidores"] * carga["replicas_entrega"])
    f = flink(eventos_s, carga, e["flink"])
    pantallas_flink = entrega("go")   # Flink no habla WebSocket: la línea base también lleva esa pieza
    unitario = sns_sqs(eventos_s, carga, e["sns_fifo"], e["sqs_fifo"])
    empaquetado = sns_sqs(eventos_s, carga, e["sns_fifo"], e["sqs_fifo"], eventos_por_mensaje=10)
    administrado = msk(eventos_s, carga, e["msk"], tr)
    candidatos = [
        (BASE, "Kinesis + Flink", k["usd"], 0.0,
         None if pantallas_flink is None else {"usd": f["usd"] + pantallas_flink["usd"]},
         f"{k['shards']} shards, {f['kpu_por_aplicacion']} KPU por aplicación, más la pieza WebSocket"),
        ("kinesis-propio", "Kinesis + propio", k_propio["usd"], 0.0, entrega("go"),
         f"{k['shards']} shards, cada réplica lee todo el stream"),
        ("sqs-centrifugo", "SQS FIFO + Centrifugo", unitario["usd"], 0.0, entrega("centrifugo"),
         "un evento por mensaje"),
        ("sqs-paquetes", "SQS FIFO empaquetado", empaquetado["usd"], 0.0, entrega("go"),
         "consumidor propio que desarma el paquete"),
        ("msk-centrifugo", "MSK + Centrifugo", administrado["usd"],
         administrado["usd_transferencia"], entrega("centrifugo"), f"{administrado['brokers']} brokers Express"),
    ]
    for transporte, nombre in (("redpanda", "Redpanda + Centrifugo"), ("nats", "NATS + Centrifugo")):
        b = propio(transporte)
        if b is not None:
            candidatos.append((f"{transporte}-centrifugo", nombre, b["usd"], b["usd_transferencia"],
                               entrega("centrifugo"), f"{b['nodos']} nodos de {b['vcpu_por_nodo']} vCPU"))
    salida = []
    for id_, nombre, usd_transporte, usd_transferencia, pieza, nota in candidatos:
        if pieza is None:
            continue
        salida.append({"id": id_, "nombre": nombre, "nota": nota, "usd_transporte": usd_transporte,
                       "usd_transferencia": usd_transferencia, "usd_entrega": pieza["usd"],
                       "usd_total": usd_transporte + usd_transferencia + pieza["usd"]})
    return salida


def equilibrio(usd_base: float, usd_camino: float, usd_hora_caida: float) -> float:
    """Horas caídas al mes que igualan la diferencia de costo con la línea base.

    Positivo: el camino es más caro, y solo conviene si evita al menos esas horas de caída.
    Negativo: es más barato, y sigue conviniendo aunque sume hasta esas horas de caída.
    """
    return (usd_camino - usd_base) / usd_hora_caida


def sensibilidad_flink(eventos_s: float, e: dict) -> dict:
    """El costo de Flink si una KPU procesa la mitad o el doble de lo supuesto."""
    return {nombre: flink(eventos_s, e["carga"], e["flink"], factor)["usd"]
            for nombre, factor in (("mitad", 0.5), ("supuesto", 1.0), ("doble", 2.0))}


def modelo(e: dict, medidos: dict) -> dict:
    """Todos los escenarios, con el punto de equilibrio de cada camino contra la línea base."""
    escenarios = []
    for esc in e["escenario"]:
        filas = caminos(esc["eventos_s"], e, medidos)
        base = next(c["usd_total"] for c in filas if c["id"] == BASE)
        for c in filas:
            c["equilibrio_h"] = {str(usd): equilibrio(base, c["usd_total"], usd) for usd in e["carga"]["usd_hora_caida"]}
        escenarios.append({**esc, "caminos": filas, "flink": sensibilidad_flink(esc["eventos_s"], e)})
    return {"escenarios": escenarios, "base": BASE}
