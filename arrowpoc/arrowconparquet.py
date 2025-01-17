import pyarrow as pa
import pyarrow.parquet as pq

# Crear una tabla Arrow
data = {
    "id": [1, 2, 3],
    "value": [0.5, 0.75, 0.9]
}
table = pa.table(data)

# Escribir la tabla en un archivo Parquet
pq.write_table(table, "example.parquet")

# Leer el archivo Parquet
loaded_table = pq.read_table("example.parquet")

print("Tabla cargada desde Parquet:")
print(loaded_table)