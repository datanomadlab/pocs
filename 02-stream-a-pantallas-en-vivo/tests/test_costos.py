"""El modelo de costos contra cuentas hechas a mano con los precios de escenario.toml."""
import copy
import tomllib

import pytest

from stream import config, costos

E = tomllib.loads(config.ESCENARIO.read_text(encoding="utf-8"))
CARGA = E["carga"]
MEDIDOS = {"tasa": 10_000, "entrega": {"go": 0.2, "centrifugo": 0.4}, "transporte": {"redpanda": 0.2, "nats": 0.3}}


def test_volumen_mensual():
    eventos, gb = costos.volumen(10_000, CARGA)
    assert eventos == 26_280_000_000
    assert gb == pytest.approx(7_884)


def test_kinesis_a_10_000_eventos_por_segundo():
    # 10 shards por registros / 0,7 de llenado = 15. Shards 164,25 + escritura 367,92
    # + fan-out de 3 consumidores: 3 × 164,25 + 3 × 7.884 GB × 0,013 = 800,23.
    k = costos.kinesis(10_000, CARGA, E["kinesis"])
    assert k["shards"] == 15
    assert k["usd"] == pytest.approx(164.25 + 367.92 + 492.75 + 307.476)


def test_kinesis_sin_fan_out_no_cobra_por_consumidor():
    k = costos.kinesis(10_000, CARGA, {**E["kinesis"], "fan_out": False})
    assert k["usd"] == pytest.approx(164.25 + 367.92)


def test_kinesis_justo_en_el_limite_de_un_shard():
    k = E["kinesis"]
    assert costos.kinesis(700, CARGA, k)["shards"] == 1      # 0,7 shards de registros / 0,7
    assert costos.kinesis(701, CARGA, k)["shards"] == 2


def test_kinesis_con_eventos_grandes_manda_el_limite_de_bytes():
    grande = {**CARGA, "bytes_por_evento": 30_000}
    k = costos.kinesis(100, grande, E["kinesis"])
    assert k["shards"] == 5                                    # 3 MB/s / 1 MB/s / 0,7
    eventos, _ = costos.volumen(100, grande)
    sin_fan_out = costos.kinesis(100, grande, {**E["kinesis"], "fan_out": False})["usd"]
    assert sin_fan_out == pytest.approx(5 * 0.015 * 730 + eventos * 2 / 1e6 * 0.014)  # 30 KB = 2 unidades


def test_flink_cobra_la_kpu_de_orquestacion_por_aplicacion():
    # 3 MB/s a 1 MB/s por KPU = 3 de proceso + 1 de orquestación. Las 4 pagan 0,11 × 730 = 80,30;
    # solo las 3 de proceso pagan 50 GB × 0,10 = 5. Por 3 aplicaciones.
    f = costos.flink(10_000, CARGA, E["flink"])
    assert f["kpu_por_aplicacion"] == 4
    assert f["usd"] == pytest.approx(3 * (4 * 80.30 + 3 * 5))
    assert costos.flink(3_333, CARGA, E["flink"])["kpu_por_aplicacion"] == 2      # justo bajo 1 MB/s
    assert costos.flink(3_334, CARGA, E["flink"])["kpu_por_aplicacion"] == 3      # justo sobre


def test_kinesis_cobra_el_fan_out_por_cada_lector():
    k = costos.kinesis(10_000, CARGA, E["kinesis"], lectores=6)
    assert k["usd"] == pytest.approx(164.25 + 367.92 + 6 * (164.25 + 7_884 * 0.013))


def test_msk_se_dimensiona_por_salida_y_en_multiplos_de_tres():
    args = (CARGA, E["msk"], E["transferencia"])
    assert costos.msk(10_000, *args)["brokers"] == 3
    # 30 MB/s de entrada y 90 de salida: 90 / 31,2 / 0,5 = 5,8 -> 6 brokers, dos por zona.
    assert costos.msk(100_000, *args)["brokers"] == 6


def test_fargate_elige_el_tamano_que_alcanza():
    # 0,2 núcleos / 0,5 de utilización = 0,4 -> tarea de 0,5 vCPU y 1 GB; 2 réplicas × 3 consumidores.
    f = costos.fargate(0.2, 10_000, 10_000, CARGA, E["fargate"])
    assert (f["vcpu"], f["tareas"]) == (0.5, 6)
    assert f["usd"] == pytest.approx(6 * (0.5 * 0.03238 + 1 * 0.00356) * 730)


def test_fargate_reparte_en_varias_tareas_sobre_el_tamano_maximo():
    f = costos.fargate(0.2, 10_000, 1_000_000, CARGA, E["fargate"])   # necesita 40 vCPU
    assert (f["vcpu"], f["tareas"]) == (16, 3 * 2 * 3)


def test_brokers_propios_la_transferencia_pesa_mas_que_las_instancias():
    b = costos.brokers_propios(0.2, 10_000, 10_000, CARGA, E["ec2"], E["transferencia"])
    assert (b["nodos"], b["vcpu_por_nodo"]) == (3, 2)
    assert b["usd"] == pytest.approx(3 * 0.0816 * 730)
    replicacion = 2 * 7_884 * 0.02
    clientes = 4 * 7_884 * 0.667 * 0.02
    assert b["usd_transferencia"] == pytest.approx(replicacion + clientes)
    assert b["usd_transferencia"] > b["usd"]


def test_brokers_propios_crecen_de_tipo_y_despues_en_cantidad():
    args = (CARGA, E["ec2"], E["transferencia"])
    assert costos.brokers_propios(0.2, 10_000, 80_000, *args)["vcpu_por_nodo"] == 4     # necesita 3,2
    assert costos.brokers_propios(0.2, 10_000, 200_000, *args)["nodos"] == 6            # necesita 8


def test_sns_y_sqs_un_evento_por_mensaje():
    # 2.628 M de lotes. SNS: 788,40 + 134,03 + 788,40 + 23,65. SQS: 3 colas × 2.628 M × 2 × 0,50.
    s = costos.sns_sqs(10_000, CARGA, E["sns_fifo"], E["sqs_fifo"])
    assert s["usd_sns"] == pytest.approx(788.4 + 134.028 + 788.4 + 23.652)
    assert s["usd_sqs"] == pytest.approx(7_884)


def test_sns_y_sqs_empaquetar_divide_las_solicitudes():
    uno = costos.sns_sqs(10_000, CARGA, E["sns_fifo"], E["sqs_fifo"])
    diez = costos.sns_sqs(10_000, CARGA, E["sns_fifo"], E["sqs_fifo"], eventos_por_mensaje=10)
    assert diez["usd_sqs"] == pytest.approx(uno["usd_sqs"] / 10)


def test_sqs_cobra_un_lote_grande_por_trozos_de_64_kb():
    grande = {**CARGA, "bytes_por_evento": 10_000}            # lote de 10 = 100 KB = 2 trozos
    s = costos.sns_sqs(1_000, grande, E["sns_fifo"], E["sqs_fifo"])
    lotes = 1_000 * 3600 * 730 / 10
    assert s["usd_sqs"] == pytest.approx(3 * lotes * 2 * 2 / 1e6 * 0.50)


def test_equilibrio_tiene_signo():
    assert costos.equilibrio(1_000, 3_000, 1_000) == pytest.approx(2.0)     # más caro: debe evitar 2 h
    assert costos.equilibrio(1_000, 500, 1_000) == pytest.approx(-0.5)      # más barato: aguanta 0,5 h más
    assert costos.equilibrio(1_000, 1_000, 1_000) == 0


def test_un_camino_sin_medicion_queda_fuera():
    sin_nats = copy.deepcopy(MEDIDOS)
    del sin_nats["transporte"]["nats"]
    ids = [c["id"] for c in costos.caminos(10_000, E, sin_nats)]
    assert "nats-centrifugo" not in ids and "redpanda-centrifugo" in ids


def test_la_linea_base_lleva_la_pieza_websocket_y_el_propio_lee_por_replica():
    filas = {c["id"]: c for c in costos.caminos(10_000, E, MEDIDOS)}
    pieza = costos.fargate(0.2, 10_000, 10_000, CARGA, E["fargate"])["usd"]
    assert filas[costos.BASE]["usd_entrega"] == pytest.approx(costos.flink(10_000, CARGA, E["flink"])["usd"] + pieza)
    assert filas["kinesis-propio"]["usd_transporte"] == pytest.approx(costos.kinesis(10_000, CARGA, E["kinesis"], 6)["usd"])
    assert filas[costos.BASE]["usd_transporte"] == pytest.approx(costos.kinesis(10_000, CARGA, E["kinesis"])["usd"])


def test_modelo_calcula_el_equilibrio_contra_la_linea_base():
    m = costos.modelo(E, MEDIDOS)
    assert [e["eventos_s"] for e in m["escenarios"]] == [1_000, 10_000, 100_000]
    for escenario in m["escenarios"]:
        base = next(c for c in escenario["caminos"] if c["id"] == costos.BASE)
        assert all(v == 0 for v in base["equilibrio_h"].values())
        for c in escenario["caminos"]:
            assert c["usd_total"] == pytest.approx(c["usd_transporte"] + c["usd_transferencia"] + c["usd_entrega"])
            assert c["equilibrio_h"]["1000"] == pytest.approx((c["usd_total"] - base["usd_total"]) / 1_000)


def test_sensibilidad_de_flink():
    s = costos.sensibilidad_flink(100_000, E)
    assert s["mitad"] > s["supuesto"] > s["doble"]
