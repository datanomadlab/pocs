import datetime as dt

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from lakehouse import config, consultas, datos, reporte, tabla


def _crudo(inicios: list[dt.datetime]) -> pa.Table:
    """Una tabla con la forma de los Parquet de TLC (nombres y tipos de origen)."""
    n = len(inicios)
    columnas = {}
    for origen, (_, tipo) in config.COLUMNAS.items():
        if origen == "tpep_pickup_datetime":
            columnas[origen] = pa.array(inicios, pa.timestamp("us"))
        elif origen == "tpep_dropoff_datetime":
            columnas[origen] = pa.array([t + dt.timedelta(minutes=10) for t in inicios], pa.timestamp("us"))
        elif tipo == pa.string():
            columnas[origen] = pa.array(["N"] * n)
        elif origen == "passenger_count":
            columnas[origen] = pa.array([None] + [1.0] * (n - 1), pa.float64())  # TLC lo trae como double
        elif tipo == pa.int64():
            columnas[origen] = pa.array([1] * n, pa.int32())
        else:
            columnas[origen] = pa.array([10.0] * n, pa.float64())
    return pa.table(columnas)


@pytest.fixture
def tabla_chica(tmp_path):
    enero = [dt.datetime(2024, 1, 5, 8), dt.datetime(2024, 1, 6, 9), dt.datetime(2009, 1, 1)]
    febrero = [dt.datetime(2024, 2, 1, 18), dt.datetime(2024, 3, 1)]
    rutas = {}
    for mes, inicios in (("2024-01", enero), ("2024-02", febrero)):
        rutas[mes] = tmp_path / f"{mes}.parquet"
        pq.write_table(_crudo(inicios), rutas[mes])
    cat = tabla.catalogo(tmp_path / "catalogo.db", tmp_path / "bodega")
    return tabla.crear_y_cargar(rutas, cat)


def test_rango_de_diciembre_termina_en_enero_del_anio_siguiente():
    assert tabla.rango_mes("2024-12") == (dt.datetime(2024, 12, 1), dt.datetime(2025, 1, 1))


def test_normalizar_descarta_viajes_fuera_del_mes_del_archivo():
    limpia = tabla.normalizar(_crudo([dt.datetime(2024, 1, 5), dt.datetime(2009, 1, 1),
                                      dt.datetime(2024, 2, 1)]), "2024-01")
    assert limpia.num_rows == 1
    assert limpia.schema == config.ESQUEMA


def test_la_tabla_queda_particionada_por_mes_y_duckdb_la_lee(tabla_chica):
    con = consultas.conectar(tabla_chica.metadata_location, hilos=1, memoria_gib=1)
    assert consultas.filas_totales(con) == 3
    particiones = {str(p.parent.name) for p in
                   __import__("pathlib").Path(tabla_chica.location().removeprefix("file://")).rglob("*.parquet")
                   if "data" in p.parts}
    assert particiones == {"mes=2024-01", "mes=2024-02"}


def test_recargar_no_duplica_filas(tabla_chica, tmp_path):
    cat = tabla.catalogo(tmp_path / "catalogo.db", tmp_path / "bodega")
    otra = tabla.crear_y_cargar({"2024-01": tmp_path / "2024-01.parquet"}, cat)
    con = consultas.conectar(otra.metadata_location, hilos=1, memoria_gib=1)
    assert consultas.filas_totales(con) == 2


def test_las_cinco_consultas_corren_en_duckdb(tabla_chica):
    con = consultas.conectar(tabla_chica.metadata_location, hilos=1, memoria_gib=1)
    medidas = consultas.medir(con, config.cargar_consultas(), "2024-01", repeticiones=1)
    assert [m["nombre"] for m in medidas] == [c.nombre for c in config.cargar_consultas()]
    assert all(m["filas_resultado"] > 0 for m in medidas)


def test_perfil_cuenta_bytes_logicos_y_los_nulos_valen_cero(tabla_chica):
    con = consultas.conectar(tabla_chica.metadata_location, hilos=1, memoria_gib=1)
    perfil = consultas.perfil_bytes(con)
    assert set(perfil) == {"2024-01", "2024-02"}
    assert perfil["2024-01"]["inicio"] == 16            # 2 viajes x 8 bytes
    assert perfil["2024-01"]["guardado_y_reenviado"] == 6  # 2 x (2 + 1)
    assert perfil["2024-02"]["pasajeros"] == 0          # el único viaje de febrero trae NULL


def test_descarga_guarda_el_archivo_y_no_lo_baja_dos_veces(tmp_path, monkeypatch):
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "yellow_tripdata_2024-01.parquet").write_bytes(b"datos")
    monkeypatch.setattr(config, "URL_BASE", origen.as_uri())
    destino = tmp_path / "crudos"
    [ruta] = datos.descargar(["2024-01"], destino)
    assert ruta.read_bytes() == b"datos"
    (origen / "yellow_tripdata_2024-01.parquet").unlink()
    assert datos.descargar(["2024-01"], destino) == [ruta]


def test_descarga_fallida_avisa_y_no_deja_archivos_a_medias(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "URL_BASE", (tmp_path / "no-existe").as_uri())
    with pytest.raises(RuntimeError, match="No pude descargar"):
        datos.descargar(["2024-01"], tmp_path / "crudos")
    assert list((tmp_path / "crudos").iterdir()) == []


def test_consulta_de_un_mes_solo_cuenta_esa_particion():
    perfil = {"2024-01": {"inicio": 100, "distancia_millas": 10},
              "2024-02": {"inicio": 300, "distancia_millas": 30}}
    un_mes = config.Consulta("q", "", ("inicio", "distancia_millas"), solo_primer_mes=True)
    todo = config.Consulta("q", "", ("inicio",))
    assert consultas.bytes_escaneados(un_mes, perfil, "2024-01") == 110
    assert consultas.bytes_escaneados(todo, perfil, "2024-01") == 400


def test_cada_consulta_tiene_sql_para_los_dos_motores():
    for consulta in config.cargar_consultas():
        for motor in ("duckdb", "bigquery"):
            sql = consultas.sql_de(consulta, motor, "t", "2024-01")
            assert "{" not in sql and " t" in sql


def test_meses_invalidos_se_rechazan(monkeypatch):
    monkeypatch.setenv("MESES", "2024-13")
    with pytest.raises(ValueError, match="Mes inválido"):
        config.meses()
    monkeypatch.setenv("MESES", "2024-01, 2024-02")
    assert config.meses() == ["2024-01", "2024-02"]


def test_consulta_con_columna_inexistente_se_rechaza(tmp_path):
    ruta = tmp_path / "consultas.toml"
    ruta.write_text('[[consulta]]\nnombre = "x"\ndescripcion = "x"\ncolumnas = ["no_existe"]\n')
    with pytest.raises(ValueError, match="columnas desconocidas"):
        config.cargar_consultas(ruta)


def test_numeros_del_reporte_van_en_formato_espanol():
    assert reporte.es("1,378.2") == "1.378,2"


def test_reporte_marca_bigquery_como_estimado_y_muestra_los_escenarios():
    local = {"fecha": "2026-11-17", "meses": ["2024-01"], "filas": 1000, "hilos": 4, "memoria_gib": 8,
             "maquina": {"sistema": "X", "cpu": "Y", "nucleos": 8},
             "versiones": {"duckdb": "2.0.0", "pyiceberg": "0.12.0"},
             "crudos_bytes": 10**6, "bodega_bytes": 10**6, "bq_bytes_logicos_total": 10**7,
             "consultas": [{"nombre": "q1", "descripcion": "Consulta uno", "filas_resultado": 1,
                            "frio_s": 0.1, "mediana_s": 0.05, "bq_bytes_estimados": 10**8}]}
    esc = config.cargar_escenario()
    texto = reporte.markdown(local, esc, None)
    assert "estimado" in texto and "BigQuery todavía no está medido" in texto
    assert all(e["nombre"] in texto for e in esc["escenario"])
    medido = {"consultas": [{"nombre": "q1", "segundos": 1.5, "bytes_facturados": 2 * 10**8}]}
    assert "200,0 MB | 1,50 s" in reporte.markdown(local, esc, medido)
