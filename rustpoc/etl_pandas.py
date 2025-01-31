import csv
import sqlite3
import time
import pandas as pd
import psutil

def main():
    start = time.time()
    process = psutil.Process()
    
    # Extract
    df = pd.read_csv("empleados.csv")
    
    # Transform
    # Filtrar filas con salario inválido
    df = df[pd.to_numeric(df['salario'], errors='coerce').notna()]
    df['salario'] = df['salario'].astype(float)
    
    # Calcular promedio por departamento
    promedio_deptos = df.groupby('departamento')['salario'].mean().reset_index()
    
    # Load (CSV)
    promedio_deptos.to_csv("salarios_promedio_python.csv", index=False)
    
    # Load (SQLite)
    conn = sqlite3.connect('empleados_python.db')
    promedio_deptos.to_sql('salarios_promedio', conn, if_exists='replace', index=False)
    conn.close()
    
    mem_usage = process.memory_info().rss // 1_000_000  # Bytes a MB
    print(f"Tiempo: {time.time() - start:.2f}s Memoria: {process.memory_info().rss // 1024 // 1024}MB")

if __name__ == "__main__":
    main()