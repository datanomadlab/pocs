import pyarrow as pa

# Crear una tabla Arrow
data = {
    "column1": [1, 2, 3],
    "column2": ["a", "b", "c"],
    "column3": [0.1, 0.2, 0.3]
}
table = pa.table(data)

print("Tabla creada:")
print(table)