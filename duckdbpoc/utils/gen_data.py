import pandas as pd

# Crear un DataFrame de ejemplo
data = {
    "timestamp": pd.date_range("2023-01-01", periods=10, freq="D"),
    "category": ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A"],
    "value": [10, 20, 15, 40, 50, 35, 60, 70, 55, 80],
}

df = pd.DataFrame(data)

# Guardar como archivo Parquet
df.to_parquet("data/inputpoc1.parquet", index=False)
df.to_csv("data/inputpoc1.csv", index=False)
