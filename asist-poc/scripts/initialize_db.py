# scripts/initialize_db.py
import duckdb
import pandas as pd

# Asegúrate de que DATABASE_URL esté configurado correctamente en config.py
DATABASE_URL = "my_database.duckdb"  # O utiliza la variable importada desde config.py

def initialize_database():
    con = duckdb.connect(DATABASE_URL)
    
    # Crear tabla con nombres en inglés
    con.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            product VARCHAR,
            quantity INTEGER,
            saledate DATE
        )
    """)
    
    con.execute(f"""
        INSERT INTO sales 
        SELECT 
            id,
            product,
            quantity,
            saledate AS sale_date
        FROM read_csv_auto('data/sales.csv', header=true)
    """)
    
    # Índice correcto sobre product
    con.execute("CREATE INDEX IF NOT EXISTS idx_product ON sales(product)")
    
    con.close()
    print("DuckDB database initialized successfully.")

if __name__ == "__main__":
    initialize_database()
