import pyarrow as pa

# Crear un Arrow Array
array = pa.array([1, 2, 3, 4, 5])

# Filtrar el array
mask = pa.array([True, False, True, False, True])
filtered_array = array.filter(mask)

print("Array original:", array)
print("Array filtrado:", filtered_array)