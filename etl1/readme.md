# Prueba de Concepto (POC): Flujo ETL usando PySpark, PostgreSQL y MySQL

Este proyecto implementa una prueba de concepto (POC) para un flujo ETL (Extract, Transform, Load) utilizando PySpark como motor de procesamiento distribuido, PostgreSQL como origen de datos, y MySQL como destino. También incluye la funcionalidad para procesar datos desde un archivo CSV hacia MySQL.

---

## **Requisitos Previos**

### **Herramientas Necesarias:**
- Docker y Docker Compose
- Python 3.8+
- Conectores JDBC para PostgreSQL y MySQL
- Paquetes Python listados en `requirements.txt`

### **Instalación de Dependencias:**

1. Crear un entorno virtual (opcional):
   ```bash
   python3 -m venv env
   source env/bin/activate  # Windows: .\env\Scripts\activate
   ```

2. Instalar los paquetes necesarios:
   ```bash
   pip install -r requirements.txt
   ```

---

## **Iniciar Servicios con Docker**

1. Inicia los contenedores de PostgreSQL y MySQL:
   ```bash
   docker-compose up -d
   ```

2. Verifica que los servicios estén corriendo:
   ```bash
   docker ps
   ```

---

## **Preparar las Bases de Datos**

1. Crear las tablas en PostgreSQL y MySQL:
   ```bash
   docker exec -i postgres_db psql -U test_user -d test_db < scripts/create_tables_psql.sql
   docker exec -i mysql_db mysql -u test_user -ptest_password test_db < scripts/create_tables_mysql.sql
   ```

2. Poblar PostgreSQL con datos ficticios:
   ```bash
   python src/utils/data_generator.py
   ```

---

## **Ejecución del ETL (PostgreSQL a MySQL)**

1. Asegúrate de que los conectores JDBC estén disponibles en `src/utils`:
   - `postgresql-connector.jar`
   - `mysql-connector.jar`

2. Ejecuta el ETL con PySpark:
   ```bash
   python src/etl/postgres_to_mysql_etl.py
   ```

3. Verifica los datos cargados en MySQL:
   ```bash
   docker exec -it mysql_db mysql -u test_user -ptest_password test_db
   SELECT COUNT(*) FROM transformed_records;
   ```

---

## **Procesar un Archivo CSV hacia MySQL**

1. Genera un archivo CSV consistente con el esquema:
   ```bash
   python generate_csv_example.py
   ```

2. Ejecuta el ETL para cargar el CSV en MySQL:
   ```bash
   python src/etl/csv_to_mysql_etl.py
   ```

3. Verifica los datos cargados en MySQL:
   ```bash
   docker exec -it mysql_db mysql -u test_user -ptest_password test_db
   SELECT COUNT(*) FROM transformed_records;
   ```

---

## **Visualización de Datos**

### PostgreSQL (Origen):
1. Conéctate al contenedor PostgreSQL:
   ```bash
   docker exec -it postgres_db psql -U test_user -d test_db
   ```
2. Consulta datos:
   ```sql
   SELECT * FROM records LIMIT 10;
   ```

### MySQL (Destino):
1. Conéctate al contenedor MySQL:
   ```bash
   docker exec -it mysql_db mysql -u test_user -ptest_password test_db
   ```
2. Consulta datos:
   ```sql
   SELECT * FROM transformed_records LIMIT 10;
   ```

---

## **Estructura del Proyecto**

```
.
├── docker-compose.yml
├── requirements.txt
├── scripts/
│   ├── create_tables.sql
├── src/
│   ├── data/
│   │   ├── sample_data.csv
│   ├── etl/
│   │   ├── postgres_to_mysql_etl.py
│   │   ├── csv_to_mysql_etl.py
│   ├── utils/
│       ├── data_generator.py
│       ├── generate_csv_example.py
│       ├── postgresql-connector.jar
│       ├── mysql-connector.jar
```

---

## **Próximos Pasos**

1. Optimizar el procesamiento distribuido para grandes volúmenes de datos.
2. Implementar validaciones y manejo de errores en el ETL.
3. Integrar pruebas unitarias para verificar transformaciones.

---

## **Comandos Relevantes**

- **Iniciar servicios:**
  ```bash
  docker-compose up -d
  ```

- **Crear tablas:**
  ```bash
  docker exec -i postgres_db psql -U test_user -d test_db < scripts/create_tables_psql.sql
  docker exec -i mysql_db mysql -u test_user -ptest_password test_db < scripts/create_tables_mysql.sql
  ```

- **Generar datos de prueba:**
  ```bash
  python src/utils/data_generator.py
  ```

- **Ejecutar ETL (PostgreSQL a MySQL):**
  ```bash
  python src/etl/postgres_to_mysql_etl.py
  ```

- **Ejecutar ETL (CSV a MySQL):**
  ```bash
  python src/etl/csv_to_mysql_etl.py
  ```

