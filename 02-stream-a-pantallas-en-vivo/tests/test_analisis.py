from stream import analisis

# Tramos de 200 ms: [ms desde el inicio, eventos, p99 en ms, máximo en ms].
NORMAL = [2000, 15]


def _serie(estados: list[tuple[int, int, int]]) -> list[list[int]]:
    return [[(i + 1) * 200, n, p99, p99] for i, (n, p99, _) in enumerate(estados)]


def test_perdidos_nunca_es_negativo():
    assert analisis.perdidos(1_000, 990) == 10
    assert analisis.perdidos(1_000, 1_000) == 0
    assert analisis.perdidos(1_000, 1_001) == 0


def test_sin_tramos_vacios_la_pantalla_no_se_congela():
    serie = _serie([(2000, 15, 0)] * 20)
    r = analisis.corte(serie, corte_ms=1000, fin_carga_ms=4000, tramo_ms=200, p99_max_ms=1000)
    assert r == {"congelada_s": 0.0, "al_dia_s": 0.0, "atraso_max_s": 0.015}


def test_corte_con_congelamiento_y_puesta_al_dia():
    # Corte a los 1.000 ms. Vacío de 1.200 a 3.000; vuelve en el tramo de 3.200 con atraso; al día desde 4.000.
    estados = [(2000, 15, 0)] * 5 + [(0, 0, 0)] * 10 + [(9000, 2100, 0)] * 4 + [(2000, 15, 0)] * 6
    r = analisis.corte(_serie(estados), corte_ms=1000, fin_carga_ms=5000, tramo_ms=200, p99_max_ms=1000)
    assert r["congelada_s"] == 2.0          # volvió en el tramo que cierra a los 3.200, o sea desde los 3.000
    assert r["al_dia_s"] == 2.8             # último tramo malo: el de 3.800
    assert r["atraso_max_s"] == 2.1


def test_corte_del_que_no_se_vuelve():
    estados = [(2000, 15, 0)] * 5 + [(0, 0, 0)] * 20
    r = analisis.corte(_serie(estados), corte_ms=1000, fin_carga_ms=5000, tramo_ms=200, p99_max_ms=1000)
    assert r["congelada_s"] is None and r["al_dia_s"] is None


def test_aguanta_exige_tasa_completa_sin_perdida_y_a_tiempo():
    fase = {"confirmados": 120_000, "atraso_generador_ms": 0, "perdidos": 0, "latencia_ms": {"p99": 40.0}}
    assert analisis.aguanta(fase, 10_000, 12, 1_000)
    assert not analisis.aguanta({**fase, "perdidos": 1}, 10_000, 12, 1_000)
    assert not analisis.aguanta({**fase, "latencia_ms": {"p99": 1_001.0}}, 10_000, 12, 1_000)
    assert not analisis.aguanta({**fase, "confirmados": 100_000}, 10_000, 12, 1_000)      # el generador no dio la tasa
    assert not analisis.aguanta({**fase, "atraso_generador_ms": 1_500}, 10_000, 12, 1_000)


def test_peor_por_columna_no_exige_que_los_peores_sean_del_mismo_corte():
    a = {"perdidos": 0, "duplicados": 8_400, "desordenados": 41,
         "corte": {"congelada_s": 44.7, "al_dia_s": 45.7, "atraso_max_s": 45.2}}
    b = {"perdidos": 12, "duplicados": 23_600, "desordenados": 3,
         "corte": {"congelada_s": 42.9, "al_dia_s": None, "atraso_max_s": 43.3}}
    peor = analisis.peor_por_columna([a, b])
    assert (peor["perdidos"], peor["duplicados"], peor["desordenados"]) == (12, 23_600, 41)
    assert peor["corte"] == {"congelada_s": 44.7, "al_dia_s": None, "atraso_max_s": 45.2}


def test_lineas_no_cuenta_vacias_ni_comentarios(tmp_path):
    archivo = tmp_path / "a.go"
    archivo.write_text("// comentario\n\npackage main\n\n/*\n * bloque\n */\nfunc main() {} // al final cuenta\n# otro\n")
    assert analisis.lineas(archivo) == 2
    assert analisis.lineas_de(tmp_path, ["{transporte}.go"], "a") == 2


def test_peor_corte_prefiere_el_que_no_volvio_y_despues_el_mas_largo():
    def fase(congelada, perdidos=0):
        return {"corte": {"congelada_s": congelada}, "perdidos": perdidos, "duplicados": 0}
    assert analisis.peor_corte([fase(0.4), fase(30.0), fase(2.0)])["corte"]["congelada_s"] == 30.0
    assert analisis.peor_corte([fase(45.0), fase(None)])["corte"]["congelada_s"] is None
    assert analisis.peor_corte([fase(0.0, 10), fase(0.0, 300)])["perdidos"] == 300
