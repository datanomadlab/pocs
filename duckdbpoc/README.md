# Configuración de Metabase con DuckDB utilizando Docker

Este documento describe cómo configurar Metabase para conectarse a una base de datos DuckDB utilizando Docker. La configuración incluye la creación de un contenedor personalizado para Metabase que instala las dependencias necesarias y permite la conexión a DuckDB mediante JDBC.

---

## **1. Requisitos Previos**

Antes de comenzar, asegúrate de tener instalados los siguientes programas en tu sistema:

- **Docker**: [Descargar Docker](https://www.docker.com/get-started)
- **Docker Compose**: Incluido en la instalación de Docker Desktop o instalable por separado.

---

## **2. Estructura del Proyecto**

Organiza los archivos de tu proyecto de la siguiente manera:

```
metabase_duckdb_project/
├── data/                     # Carpeta para almacenar la base de datos DuckDB
│   └── (vacía inicialmente, se creará el archivo my_database.duckdb)
├── plugins/                  # Carpeta para almacenar el controlador JDBC de DuckDB
│   └── duckdb_jdbc.jar
├── init/                     # Carpeta para scripts de inicialización
│   ├── setup_duckdb.py       # Script para inicializar la base de datos DuckDB
│   ├── ingest_csv.py         # Script para ingerir datos desde CSV
│   ├── ingest_parquet.py     # Script para ingerir datos desde Parquet
│   ├── analyze_data.py       # Script para realizar análisis SQL
│   ├── poc1.py               # Script para poc1 creacion de dataframe en memoria de duckdb
├── Dockerfile                # Dockerfile para personalizar Metabase
├── docker-compose.yml        # Archivo para configurar los servicios Docker
└── README.md                 # Documentación (este archivo)
```
Visualizar la base de datos:
```
duckdb D SELECT * FROM read_parquet('../data/output....');
duckdb my_database.duckdb
```
---

## **3. Configuración Paso a Paso**

### **Paso 1: Crear Scripts de Inicialización y Procesamiento de Datos**

#### **1. Script para Inicializar DuckDB**

Crea un archivo `init/setup_duckdb.py` con el siguiente contenido:

```python
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
```

#### **2. Script para Ingerir Datos desde CSV**

Crea un archivo `init/ingest_csv.py`:

```python
import duckdb

# Ingerir datos desde un archivo CSV a DuckDB
def ingest_csv(database_path, csv_path):
    conn = duckdb.connect(database_path)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS csv_data AS
        SELECT * FROM read_csv_auto('{csv_path}')
    """)
    print("Datos CSV ingeridos exitosamente.")
    conn.close()

if __name__ == "__main__":
    ingest_csv("/data/my_database.duckdb", "/data/input.csv")
```

#### **3. Script para Ingerir Datos desde Parquet**

Crea un archivo `init/ingest_parquet.py`:

```python
import duckdb

# Ingerir datos desde un archivo Parquet a DuckDB
def ingest_parquet(database_path, parquet_path):
    conn = duckdb.connect(database_path)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS parquet_data AS
        SELECT * FROM read_parquet('{parquet_path}')
    """)
    print("Datos Parquet ingeridos exitosamente.")
    conn.close()

if __name__ == "__main__":
    ingest_parquet("/data/my_database.duckdb", "/data/input.parquet")
```

#### **4. Script para Realizar Análisis SQL**

Crea un archivo `init/analyze_data.py`:

```python
import duckdb

# Ejecutar un análisis SQL en DuckDB
def analyze_data(database_path):
    conn = duckdb.connect(database_path)
    result = conn.execute("""
        SELECT category, SUM(value) AS total_sales
        FROM sales
        GROUP BY category
        ORDER BY total_sales DESC
    """).fetchdf()
    print("Análisis completado:")
    print(result)
    conn.close()

if __name__ == "__main__":
    analyze_data("/data/my_database.duckdb")
```

---

### **Paso 2: Descargar el Controlador JDBC de DuckDB**

1. Descarga el controlador JDBC de DuckDB desde la página oficial de [DuckDB Releases](https://github.com/duckdb/duckdb/releases).
2. Coloca el archivo descargado (por ejemplo, `duckdb.metabase-driver.jar`) en la carpeta `plugins`.

---

### **Paso 3: Crear el Dockerfile para Metabase**

Crea un archivo `Dockerfile` con el siguiente contenido:

```dockerfile
FROM debian:bullseye-slim

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y \
    default-jre \
    libstdc++6 \
    libc6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Descargar Metabase
WORKDIR /app
RUN curl -L https://downloads.metabase.com/v0.51.10/metabase.jar -o metabase.jar

# Exponer el puerto 3000
EXPOSE 3000

# Agregar punto de entrada
CMD ["java", "-jar", "metabase.jar"]
```

---

### **Paso 4: Configurar `docker-compose.yml`**

Crea un archivo `docker-compose.yml` con la siguiente configuración:

```yaml
version: "3.9"
services:
  metabase:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: metabase
    ports:
      - "3000:3000"
    volumes:
      - ./plugins:/plugins       # Montar el controlador JDBC
      - ./data:/data             # Montar la base de datos DuckDB
    environment:
      MB_PLUGINS_DIR: /plugins   # Ruta al plugin JDBC
    depends_on:
      - duckdb-init

  duckdb-init:
    image: python:3.9-slim
    container_name: duckdb_init
    volumes:
      - duckdb-data:/data
      - ./init:/init
    working_dir: /init
    entrypoint: ["sh", "-c", "pip install duckdb pandas && python setup_duckdb.py"]

volumes:
  duckdb-data:
```

---

### **Paso 5: Construir e Iniciar los Contenedores**

Ejecuta los siguientes comandos:

1. **Construir y levantar los servicios:**
   ```bash
   docker-compose up --build
   ```

2. **Verificar los logs:**
   Asegúrate de que no haya errores en la inicialización.

---

### **Paso 6: Configurar Metabase**

1. Abre Metabase en tu navegador en [http://localhost:3000](http://localhost:3000).
2. Sigue las instrucciones para crear una cuenta.
3. Ve a **Administración > Bases de Datos > Agregar Base de Datos**.
4. Selecciona **Otro (otro tipo de base de datos)**.
5. Configura la

