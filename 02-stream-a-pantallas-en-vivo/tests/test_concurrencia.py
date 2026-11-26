from stream import concurrencia, config


def test_cada_pantalla_mira_una_cuenta():
    for e in (*concurrencia.ESCENARIOS, concurrencia.ESCENARIO_RAPIDO):
        assert e.pantallas == e.cuentas * e.espectadores
        assert e.entregas_s == e.tasa * e.espectadores


def test_parametros_de_un_escenario(monkeypatch):
    monkeypatch.delenv("ESPECTADORES", raising=False)
    base = config.parametros()
    assert base.espectadores == 1      # sin la variable, cada cuenta la mira una sola pantalla
    e = concurrencia.Escenario("x", 500, 4_000, 40, 5)
    p = concurrencia.parametros_de(base, e)
    assert (p.tasa, p.emisores, p.cuentas, p.pantallas, p.espectadores) == (500, 4_000, 40, 200, 5)
    assert p.rapido is False and p.bytes == concurrencia.BYTES_EVENTO


def _fase(confirmados, unicos, copias, p99=5.0, duplicados=0):
    return {"confirmados": confirmados, "unicos": unicos, "copias": copias, "perdidos": confirmados - unicos,
            "duplicados": duplicados,
            "atraso_generador_ms": 0, "latencia_ms": {"p50": 1.0, "p99": p99}, "tasa": 100, "reconexiones": 0}


def test_las_entregas_suman_a_todos_los_espectadores():
    f = concurrencia.con_entregas(_fase(1_000, 1_000, 4_000), espectadores=5)
    assert (f["entregas"], f["entregas_esperadas"]) == (5_000, 5_000)
    assert concurrencia.aguanta(f, 100, 10, 1_000)
    assert "5.000 de 5.000" in concurrencia.linea(f)


def test_no_aguanta_si_un_espectador_recibe_menos():
    # La pantalla principal recibió todo, pero a las demás les faltó el 10 %.
    f = concurrencia.con_entregas(_fase(1_000, 1_000, 3_600), espectadores=5)
    assert not concurrencia.aguanta(f, 100, 10, 1_000)


def test_un_repetido_no_tapa_una_entrega_que_falto():
    # La principal vio 50 repetidos: se supone que las otras 4 pantallas de cada cuenta también.
    f = concurrencia.con_entregas(_fase(1_000, 1_000, 4_000, duplicados=50), espectadores=5)
    assert f["entregas"] == 1_000 + 4_000 - 50 * 4
    assert not concurrencia.aguanta(f, 100, 10, 1_000)


def test_las_entregas_no_cambian_la_fase_original():
    original = _fase(1_000, 1_000, 4_000)
    concurrencia.con_entregas(original, espectadores=5)
    assert "entregas" not in original


def test_no_aguanta_si_el_p99_se_pasa():
    f = concurrencia.con_entregas(_fase(1_000, 1_000, 4_000, p99=1_500.0), espectadores=5)
    assert not concurrencia.aguanta(f, 100, 10, 1_000)
