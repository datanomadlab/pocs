# modules/database.py
import pandas as pd
from pathlib import Path
import duckdb

CSV_PATH = Path(__file__).parent.parent / 'data' / 'sales.csv'

def ejecutar_query(query: str):
    """Ejecuta una consulta SQL en la base de datos DuckDB"""
    # Conexión a la base de datos DuckDB
    conn = duckdb.connect("my_database.duckdb")
    
    try:
        # Ejecutar consulta y obtener resultados
        resultado = conn.execute(query).fetchdf()
        return resultado
    finally:
        conn.close()

def corregir_consulta(query: str) -> str:
    """
    Reemplaza nombres erróneos en la consulta generada por los nombres correctos según el esquema.
    """
    correcciones = {
        "order_date": "fecha",    # Cambia 'order_date' por 'fecha'
        "sales": "ventas"
        # Puedes agregar más conversiones si es necesario
    }
    for incorrecto, correcto in correcciones.items():
        query = query.replace(incorrecto, correcto)
    return query
