import pandas as pd
import pyarrow as pa

# Crear un DataFrame de Pandas
df = pd.DataFrame({
    "A": [10, 20, 30],
    "B": ["x", "y", "z"]
})

# Convertir DataFrame a Arrow Table
arrow_table = pa.Table.from_pandas(df)

# Convertir de Arrow Table a DataFrame
df_converted = arrow_table.to_pandas()

print("Tabla Arrow:")
print(arrow_table)
print("\nDataFrame convertido:")
print(df_converted)