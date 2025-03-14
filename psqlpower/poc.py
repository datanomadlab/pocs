import psycopg2

conn = psycopg2.connect(
    dbname="mydatabase",
    user="myuser",
    password="mysecretpassword",
    host="localhost",
    port=5432
)
cur = conn.cursor()

# Consulta: encuentra el ítem cuyo vector es más similar a [0.1, 0.2, 0.3]
cur.execute("""
SELECT id, description, embedding, embedding <-> '[0.1,0.2,0.3]'::vector AS distance
FROM items
ORDER BY distance
LIMIT 1;
""")
print("pgvector:", cur.fetchone())
conn.commit()

# Consulta: encuentra la ubicación más cercana al punto (-74.005941, 40.712784)
cur.execute("""
SELECT name, ST_Distance(geom, ST_SetSRID(ST_MakePoint(-74.005941, 40.712784),4326)) AS distance
FROM locations
ORDER BY distance
LIMIT 1;
""")
print("PostGIS:", cur.fetchone())
conn.commit()

# Consulta: busca en la tabla productos aquellos nombres similares a 'Aple iPhon'
cur.execute("SELECT * FROM products WHERE name % 'Aple iPhon';")
print("pg_trgm:", cur.fetchone())
conn.commit()

# Ejecutar una consulta para que aparezca en las estadísticas
cur.execute("SELECT 1;")
conn.commit()

# Consulta: obtener la consulta con más llamadas
cur.execute("""
SELECT query, calls
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 1;
""")
print("pg_stat_statements:", cur.fetchone())
conn.commit()

cur.close()
conn.close()



