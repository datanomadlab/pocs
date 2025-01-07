import duckdb
import matplotlib.pyplot as plt

INPUT_FILE = "./data/inputpoc1.parquet"

def generate_charts(input_file):
    conn = duckdb.connect()
    
    # Leer datos y calcular métricas
    conn.execute(f"""
        SELECT 
            category, 
            COUNT(*) AS total_rows, 
            AVG(value) AS avg_value, 
            SUM(value) AS total_value 
        FROM read_parquet('{input_file}')
        GROUP BY category
    """)
    result = conn.fetchdf()

    # Gráfico de barras: Total de filas por categoría
    plt.figure(figsize=(8, 6))
    plt.bar(result['category'], result['total_rows'])
    plt.title("Total de Filas por Categoría")
    plt.xlabel("Categoría")
    plt.ylabel("Total de Filas")
    plt.savefig("./data/total_rows_chart.png")
    plt.close()  # Cerrar la figura actual

    # Gráfico de líneas: Valor Promedio por Categoría
    plt.figure(figsize=(8, 6))
    plt.plot(result['category'], result['avg_value'], marker='o')
    plt.title("Valor Promedio por Categoría")
    plt.xlabel("Categoría")
    plt.ylabel("Valor Promedio")
    plt.savefig("./data/avg_value_chart.png")
    plt.close()  # Cerrar la figura actual

    print("Gráficos generados y guardados en el directorio 'data'.")
    conn.close()
    
    import sys
    sys.exit(0)  # Terminar el programa después de guardar las figuras

generate_charts(INPUT_FILE)
