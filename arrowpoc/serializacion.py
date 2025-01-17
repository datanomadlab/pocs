import pyarrow as pa

# Crear una tabla Arrow
data = {
    "name": ["Alice", "Bob"],
    "age": [25, 30]
}
table = pa.table(data)

# Serializar la tabla a un archivo
with pa.OSFile("example.arrow", "wb") as sink:
    writer = pa.ipc.new_file(sink, table.schema)
    writer.write(table)
    writer.close()

# Leer la tabla serializada
with pa.memory_map("example.arrow", "rb") as source:
    loaded_table = pa.ipc.open_file(source).read_all()

print("Tabla cargada desde archivo:")
print(loaded_table)