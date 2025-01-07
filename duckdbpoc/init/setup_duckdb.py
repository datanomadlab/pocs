import duckdb

# Crear una base de datos DuckDB con datos de ejemplo
def initialize_duckdb(database_path):
    conn = duckdb.connect(database_path)

    # Crear una tabla con datos de ejemplo
    conn.execute("""
        CREATE TABLE sales (
            date DATE,
            category TEXT,
            value INTEGER
        )
    """)
    conn.execute("""
        INSERT INTO sales VALUES
        ('2023-01-01', 'A', 100),
        ('2023-01-02', 'B', 200),
        ('2023-01-03', 'C', 150),
        ('2023-01-04', 'A', 300),
        ('2023-01-05', 'B', 250)
    """)
    conn.close()

if __name__ == "__main__":
    initialize_duckdb("/data/my_database.duckdb")
    print("Base de datos DuckDB inicializada.")
