
# Subir el stack de docker
docker compose up -d

# Verificar que la tabla not_clean existe en la base de datos raw
docker exec -it poc_postgres psql -U admin -d raw -c "\dt"

# Verificar que los 5 registros se han insertado en la tabla not_clean
docker exec -it poc_postgres psql -U admin -d raw -c "SELECT * FROM not_clean;"

# Crear el entorno virtual
python3 -m venv lab

# Activar el entorno virtual
source lab/bin/activate

# Instalar dbt-core y dbt-postgres
pip install dbt-core dbt-postgres

# Iniciar el proyecto dbt
dbt init

# Verificar que el proyecto se ha creado correctamente
dbt debug

