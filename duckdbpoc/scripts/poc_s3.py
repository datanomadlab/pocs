import duckdb

S3_FILE = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"


def process_from_s3(s3_file):
    conn = duckdb.connect()
    
    # Crear una vista temporal para facilitar las consultas
    conn.execute(f"""
        CREATE TEMP VIEW data AS 
        SELECT * FROM read_parquet('{s3_file}')
    """)
    
    # Mostrar la estructura de la tabla
    print("Estructura de la tabla:")
    schema = conn.execute("DESCRIBE data").fetchdf()
    print(schema)
    
    # Realizar análisis (ahora funcionará porque 'data' existe como vista)
    analysis = conn.execute("""
        SELECT payment_type, COUNT(*) AS count
        FROM data
        GROUP BY payment_type
    """).fetchdf()
    
    print("\nAnálisis desde S3:")
    print(analysis)

process_from_s3(S3_FILE)
