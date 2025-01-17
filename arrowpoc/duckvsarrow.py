# ======================
# Sección 1: Generación de datos simulados (común)
# ======================
import pyarrow as pa
import pandas as pd
import time
import psutil
import os

# Configuración del entorno
BASE_DIR = os.path.abspath("./iceberg_poc")
WAREHOUSE_DIR = os.path.join(BASE_DIR, "warehouse")
os.makedirs(WAREHOUSE_DIR, exist_ok=True)

# Generar datos grandes
print("\nGenerando datos grandes...")
num_rows = 10_000_000  # 10 millones de filas
start_time = time.time()
data = {
    'id': list(range(1, num_rows + 1)),
    'name': [f'user_{i % 1000}' for i in range(num_rows)],
    'value': [float(i % 1000) for i in range(num_rows)]
}
data_creation_time = time.time() - start_time
print(f"Datos generados en {data_creation_time:.2f} segundos.")

# Convertir datos a formatos requeridos
arrow_table = pa.Table.from_pydict(data)  # Para Apache Arrow
df = pd.DataFrame(data)  # Para DuckDB

# ======================
# Sección 2: Procesamiento con DuckDB
# ======================
import duckdb

print("\nProcesando datos con DuckDB...")
process = psutil.Process()
start_memory = process.memory_info().rss
start_time = time.time()

# Crear base de datos en memoria y ejecutar una consulta SQL
conn = duckdb.connect(database=':memory:')
conn.register("input_table", df)
result_duckdb = conn.execute("""
    SELECT name, SUM(value) AS total_value
    FROM input_table
    WHERE value > 500
    GROUP BY name
""").fetchdf()

duckdb_time = time.time() - start_time
duckdb_memory = process.memory_info().rss - start_memory

print(f"Tiempo de ejecución (DuckDB): {duckdb_time:.2f} segundos")
print(f"Memoria usada (DuckDB): {duckdb_memory / (1024 ** 2):.2f} MB")
print(result_duckdb.head())

# ======================
# Sección 3: Procesamiento con Apache Arrow
# ======================
print("\nProcesando datos con Apache Arrow...")
start_memory = process.memory_info().rss
start_time = time.time()

# Filtrar y agrupar usando Arrow
filtered_table = arrow_table.filter(pa.compute.greater(arrow_table['value'], 500))
result_arrow = filtered_table.group_by('name').aggregate([
    ('value', 'sum')
]).to_pandas()

arrow_time = time.time() - start_time
arrow_memory = process.memory_info().rss - start_memory

print(f"Tiempo de ejecución (Arrow): {arrow_time:.2f} segundos")
print(f"Memoria usada (Arrow): {arrow_memory / (1024 ** 2):.2f} MB")
print(result_arrow.head())

# ======================
# Conclusión
# ======================
print("\nComparativa de resultados:")
print(f"DuckDB - Tiempo: {duckdb_time:.2f}s, Memoria: {duckdb_memory / (1024 ** 2):.2f} MB")
print(f"Arrow - Tiempo: {arrow_time:.2f}s, Memoria: {arrow_memory / (1024 ** 2):.2f} MB")