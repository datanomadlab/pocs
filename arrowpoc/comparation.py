import pyarrow as pa
import pyarrow.parquet as pq
import os
import time
import psutil

# Configuración del entorno y directorios
BASE_DIR = os.path.abspath("./iceberg_poc")
WAREHOUSE_DIR = os.path.join(BASE_DIR, "warehouse")
os.makedirs(WAREHOUSE_DIR, exist_ok=True)

# Generar datos grandes
print("\nGenerando datos grandes...")
num_rows = 10_000_000  # 10 millones de filas
start_time = time.time()
data = pa.Table.from_pydict({
    'id': pa.array(range(1, num_rows + 1), type=pa.int64()),
    'name': pa.array([f'user_{i % 1000}' for i in range(num_rows)], type=pa.string()),
    'value': pa.array([float(i % 1000) for i in range(num_rows)], type=pa.float64())
})
data_creation_time = time.time() - start_time

print(f"Datos generados en {data_creation_time:.2f} segundos.")
print(f"Tamaño de los datos: {data.nbytes / (1024 ** 2):.2f} MB")

# Medir uso de recursos al escribir los datos
process = psutil.Process(os.getpid())
start_memory = process.memory_info().rss
start_time = time.time()

# Escribir datos en un archivo Parquet
output_file = os.path.join(WAREHOUSE_DIR, "example_table.parquet")
print("\nEscribiendo datos a Parquet...")
pq.write_table(data, output_file)

write_time = time.time() - start_time
end_memory = process.memory_info().rss
print(f"Datos escritos en {write_time:.2f} segundos.")
print(f"Uso de memoria al escribir: {(end_memory - start_memory) / (1024 ** 2):.2f} MB")

# Medir uso de recursos al leer los datos
start_memory = process.memory_info().rss
start_time = time.time()

print("\nLeyendo datos desde Parquet...")
loaded_data = pq.read_table(output_file)

read_time = time.time() - start_time
end_memory = process.memory_info().rss
print(f"Datos leídos en {read_time:.2f} segundos.")
print(f"Uso de memoria al leer: {(end_memory - start_memory) / (1024 ** 2):.2f} MB")

# Mostrar una muestra de los datos leídos
print("\nMuestra de los datos leídos:")
print(loaded_data.to_pandas().head())