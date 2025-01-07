import duckdb
import pandas as pd

# Crear una base de datos DuckDB
conn = duckdb.connect(database=':memory:')

# Crear datos con tipos complejos
complex_data = {
    'id': [1, 2, 3],
    'array_col': [[1, 2, 3], [4, 5], [6]],
    'struct_col': [{'name': 'Alice', 'age': 25}, {'name': 'Bob', 'age': 30}, {'name': 'Carol', 'age': 35}],
    'map_col': [{'key1': 'value1', 'key2': 'value2'}, {'key1': 'value3'}, {'key1': 'value4', 'key2': 'value5'}]
}

# Convertir a un DataFrame
complex_df = pd.DataFrame(complex_data)

# Registrar el DataFrame en DuckDB
conn.register('complex_data', complex_df)

# Crear una tabla en DuckDB con datos complejos
conn.execute("""
    CREATE TABLE complex_table AS
    SELECT 
        id,
        array_col,
        struct_col,
        map_col
    FROM complex_data
""")

# Consultar elementos de tipos complejos
query = """
    SELECT 
        id,
        array_length(array_col) AS array_length,
        array_col[1] AS array_col_1,
        array_col[5] AS array_col_5,
        struct_extract(struct_col, 'name') AS name,
        struct_extract(struct_col, 'age') AS age,
        map_extract(map_col, 'key1') AS key1_value,
        map_extract(map_col, 'key2') AS key2_value,
        map_extract(map_col, 'key3') AS key3_value,
    FROM complex_table
"""

result = conn.execute(query).fetchdf()

# Mostrar resultados
print("Consulta de tipos complejos:")
print(result)
