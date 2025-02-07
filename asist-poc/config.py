import os
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv(override=True)

# Acceder a la API key
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "duckdb")  # o "postgresql"
DATABASE_URL = os.getenv("DATABASE_URL", "my_database.duckdb")
ALLOWED_SQL_PREFIXES = ["SELECT"]  # Solo permitir consultas de lectura
