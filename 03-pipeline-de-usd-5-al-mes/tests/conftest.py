import pytest


def _diaria(dia: str, segundos: float) -> dict:
    return {"dia": dia, "tocadas": 3000,
            "dlt": {"segundos": segundos, "segundos_job": 1.0, "segundos_carga": 0.4, "segundos_publicar": 0.6,
                    "filas": 3000, "memoria_mb": 361.2, "archivos_nuevos": 9},
            "script": {"segundos": 0.4, "filas": 540_000}, "igual": {"dlt": True, "script": True}}


@pytest.fixture
def medicion() -> dict:
    """Una medición chica con la misma forma que escribe medir.py."""
    resultados = ["pasa", "pasa", "pasa", "pasa", "pasa", "no pasa", "pasa"]
    return {
        "fecha": "2026-11-27",
        "maquina": {"sistema": "Darwin 25.6.0", "cpu": "Apple M4 Pro", "nucleos": 14},
        "limite": {"cpus": "1", "memoria_mb": 512},
        "versiones": {"dlt": "1.32.0", "duckdb": "2.0.1", "psycopg2-binary": "2.9.13", "pyarrow": "26.0.1",
                      "postgres": "18.7", "python": "3.12.12", "docker": "29.9.3"},
        "datos": {"filas del archivo": 1_067_371, "repetidas entre las dos hojas": 22_523,
                  "filas que quedan": 1_041_449},
        "historia_hasta": "2010-11-30", "dias": ["2010-12-01", "2011-01-13"],
        "inicial": {"dlt": {"segundos": 3.1}, "script": {"segundos": 0.5}},
        "diarias": [_diaria("2010-12-01", 2.4), _diaria("2010-12-02", 2.6), _diaria("2010-12-03", 3.4)],
        "volumen_mes": {"filas": 60_000, "bytes_tocados": 6_000_000, "bytes_tablas": 90_000_000},
        "destino": {"dlt": {"archivos": 300, "bytes": 9_000_000}, "script": {"archivos": 4, "bytes": 27_000_000},
                    "archivos_crudo": 130, "imagen_bytes": 155_000_000},
        "pruebas": [{"id": i, "nombre": f"Prueba {i}", "dlt": {"resultado": r, "detalle": "detalle dlt"},
                     "script": {"resultado": "no pasa" if i % 2 else "pasa", "detalle": "detalle script"}}
                    for i, r in enumerate(resultados, 1)],
        "pruebas_detalle": {"3": {"filas_escondidas_si_solo_cargas_registradas": 2_700},
                            "5": {"pruebas_fallidas": {"precios_negativos": 1}}},
        "lineas": {"dlt": 120, "script": 18, "reportes": 60, "n_reportes": 5},
    }
