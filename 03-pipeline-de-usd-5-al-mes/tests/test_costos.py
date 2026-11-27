"""El modelo de costos con casos calculados a mano, incluidos los bordes de cada capa gratuita."""
import pytest

from pipeline import config, costos

PRECIOS = costos.cargar(config.ESCENARIO)
RUN, BUCKET, FIVETRAN = PRECIOS["cloud_run"], PRECIOS["bucket"], PRECIOS["fivetran"]


def test_cloud_run_cobra_un_minuto_como_minimo_y_redondea_a_100_ms():
    assert costos.segundos_facturados(2.5, RUN) == 60
    assert costos.segundos_facturados(61.04, RUN) == pytest.approx(61.1)
    assert costos.segundos_facturados(61.1, RUN) == pytest.approx(61.1)


def test_cloud_run_al_mes_a_mano():
    # 2,5 s + 10 s de arranque = 12,5 s, que se cobran como 60. 30 corridas: 1.800 vCPU-s y 900 GiB-s.
    esperado = 1800 * 0.000018 + 900 * 0.000002
    assert costos.cloud_run_mes(2.5, 30, RUN, capa=False) == pytest.approx(esperado)
    assert costos.cloud_run_mes(2.5, 30, RUN, capa=True) == 0


def test_cloud_run_justo_sobre_la_capa_gratuita():
    # 4.001 corridas de 60 s = 240.060 vCPU-s: 60 sobre la capa. La memoria (120.030 GiB-s) sigue gratis.
    assert costos.cloud_run_mes(0, 4001, {**RUN, "arranque_s": 0}, capa=True) == pytest.approx(60 * 0.000018)


def test_scheduler_un_job_es_gratis_con_capa():
    assert costos.scheduler_mes(1, PRECIOS["scheduler"], capa=True) == 0
    assert costos.scheduler_mes(1, PRECIOS["scheduler"], capa=False) == pytest.approx(0.10)


def test_bucket_cobra_solo_lo_que_pasa_de_5_gb():
    assert costos.bucket_mes(5 * 2**30, 0, 0, BUCKET, capa=True) == 0
    assert costos.bucket_mes(6 * 2**30, 0, 0, BUCKET, capa=True) == pytest.approx(0.020)
    assert costos.bucket_mes(0, 6000, 60000, BUCKET, capa=True) == pytest.approx(1 * 0.005 + 10 * 0.0004)


def test_registro_gratis_hasta_medio_gb():
    assert costos.registro_mes(0.5 * 2**30, PRECIOS["registro"], capa=True) == 0
    assert costos.registro_mes(2**30, PRECIOS["registro"], capa=False) == pytest.approx(0.10)


def test_fivetran_plan_gratuito_y_tramos():
    assert costos.fivetran_mes(500_000, FIVETRAN, capa=True) == 0
    assert costos.fivetran_mes(500_001, FIVETRAN, capa=True) == pytest.approx(5 + 0.500001 * 495)
    assert costos.fivetran_mes(200_000, FIVETRAN, capa=False) == pytest.approx(5 + 0.2 * 495)
    assert costos.fivetran_mes(2_000_000, FIVETRAN, capa=False) == pytest.approx(500 + 170)
    assert costos.fivetran_mes(5_000_000, FIVETRAN, capa=False) == pytest.approx(1010 + 58)


def test_los_tramos_de_fivetran_no_saltan():
    # Justo en el borde de cada tramo, las dos fórmulas dan lo mismo.
    assert costos.fivetran_mes(999_999.999, FIVETRAN, capa=False) == pytest.approx(500, abs=0.01)
    assert costos.fivetran_mes(3_999_999.999, FIVETRAN, capa=False) == pytest.approx(1010, abs=0.01)


def test_airbyte_cobra_el_plan_minimo_y_los_creditos_extra():
    p = PRECIOS["airbyte"]
    assert costos.airbyte_mes(0, p) == 20
    # 1 GB en Postgres -> 2 GB serializados -> 8 créditos: 3 sobre los 5 incluidos, a USD 4.
    assert costos.airbyte_mes(1e9, p) == pytest.approx(20 + 3 * 4)


def test_bigquery_con_y_sin_capa():
    p = PRECIOS["bigquery"]
    assert costos.bigquery_mes(5 * 2**30, 0.5 * 2**40, p, capa=True) == 0
    assert costos.bigquery_mes(20 * 2**30, 2 * 2**40, p, capa=True) == pytest.approx(10 * 0.023 + 1 * 6.25)


def test_segundos_crecen_con_los_datos_salvo_el_arranque():
    assert costos.segundos_por_corrida(1.5, 0.4, 0.6, 1) == pytest.approx(2.5)
    assert costos.segundos_por_corrida(1.5, 0.4, 0.6, 100) == pytest.approx(101.5)


def test_escenarios_trae_los_dos_lados_con_y_sin_capa(medicion):
    esc = costos.escenarios(medicion, PRECIOS)
    assert [e["factor_datos"] for e in esc] == [1, 10, 100]
    for e in esc:
        assert e["nuestra"]["con_capa"]["total"] <= e["nuestra"]["sin_capa"]["total"]
        assert e["administradas"]["con_capa"]["fivetran"] <= e["administradas"]["sin_capa"]["fivetran"]
