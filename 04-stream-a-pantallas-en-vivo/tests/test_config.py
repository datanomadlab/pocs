import pytest

from stream import config
from stream.__main__ import _versiones, combinar, nucleos_medidos


def test_rutas_del_archivo_son_validas():
    rutas = config.rutas()
    assert len({r.id for r in rutas}) == len(rutas) >= 6
    assert {r.id for r in rutas if r.simulada} == {r.id for r in rutas if r.transporte in ("kinesis", "sqs")}


def test_cada_ruta_tiene_su_codigo_o_su_configuracion():
    for r in config.rutas():
        archivos = config.CODIGO[r.entrega] + config.CONFIGURACION.get(r.entrega, [])
        assert archivos
        if r.entrega == "node" and r.transporte in ("kinesis", "sqs"):
            continue
        for a in archivos:
            assert (config.RAIZ / a.format(transporte=r.transporte)).exists(), a


def test_rutas_se_filtran_por_variable(monkeypatch):
    monkeypatch.setenv("RUTAS", "nats-go, redpanda-go")
    assert [r.id for r in config.rutas()] == ["redpanda-go", "nats-go"]
    monkeypatch.setenv("RUTAS", "no-existe")
    with pytest.raises(ValueError, match="no-existe"):
        config.rutas()


def test_parametros_validan_la_entrada(monkeypatch):
    monkeypatch.setenv("TASA", "5000")
    monkeypatch.setenv("RAPIDO", "1")
    p = config.parametros()
    assert (p.tasa, p.rapido, p.segundos_nominal) == (5000, True, 10)
    monkeypatch.setenv("TASA", "muchos")
    with pytest.raises(ValueError, match="TASA"):
        config.parametros()
    monkeypatch.setenv("TASA", "0")
    with pytest.raises(ValueError, match="TASA"):
        config.parametros()


def test_las_versiones_salen_del_compose():
    v = _versiones()
    assert {"Redpanda", "NATS", "Centrifugo", "kinesis-mock", "ElasticMQ", "Zilla", "EMQX"} <= set(v)
    assert all(x[0].isdigit() for x in v.values())


def test_nucleos_medidos_promedia_solo_rutas_medidas():
    ruta = lambda transporte, entrega, t, e, etiqueta="medido": {
        "transporte": transporte, "entrega": entrega, "etiqueta": etiqueta, "nominal": {"nucleos": {"transporte": t, "entrega": e}}}
    medicion = {"parametros": {"tasa": 10_000}, "rutas": [
        ruta("redpanda", "go", 0.2, 0.3), ruta("redpanda", "centrifugo", 0.4, 0.5), ruta("nats", "go", 0.1, 0.5),
        ruta("kinesis", "go", 9, 9, "simulado"), {"transporte": "nats", "entrega": "node", "etiqueta": "medido", "error": "x"}]}
    m = nucleos_medidos(medicion)
    assert m["transporte"] == pytest.approx({"redpanda": 0.3, "nats": 0.1})
    assert m["entrega"] == pytest.approx({"go": 0.4, "centrifugo": 0.5})


def test_una_corrida_parcial_reemplaza_solo_sus_rutas():
    anteriores = [{"id": "a", "v": 1}, {"id": "b", "v": 1}, {"id": "c", "v": 1}]
    resultado = combinar(anteriores, [{"id": "b", "v": 2}, {"id": "d", "v": 2}], ["a", "b", "c", "d"])
    assert resultado == [{"id": "a", "v": 1}, {"id": "b", "v": 2}, {"id": "c", "v": 1}, {"id": "d", "v": 2}]
    assert combinar([], [{"id": "b", "v": 2}], ["a", "b"]) == [{"id": "b", "v": 2}]


def test_rutas_todas_ignora_el_filtro(monkeypatch):
    monkeypatch.setenv("RUTAS", "nats-go")
    assert len(config.rutas(todas=True)) > 1


def test_escribir_sin_comprimir_solo_se_pide_en_rutas_sobre_kafka():
    assert all(r.transporte == "redpanda" for r in config.rutas() if r.sin_comprimir)
    assert any(r.sin_comprimir for r in config.rutas())
