## Welcome to Your Medallion Architecture dbt Project

Este proyecto demuestra cómo implementar una arquitectura de datos en **tres capas** (Bronze, Silver y Gold) utilizando **dbt** y **PostgreSQL**. A continuación, encontrarás los pasos para levantar un contenedor de PostgreSQL, crear tablas de origen y poblarlas con datos de ejemplo, así como ejecutar las transformaciones con dbt.

---

### 1. Levantar el Contenedor de PostgreSQL

```bash
docker run --name postgres-dbt \
  -e POSTGRES_USER=dbt_user \
  -e POSTGRES_PASSWORD=dbt_password \
  -e POSTGRES_DB=dbt_database \
  -p 5432:5432 \
  -d postgres:15
```

Este comando ejecuta un contenedor llamado `postgres-dbt` con la base de datos `dbt_database` y credenciales de usuario.

---

### 2. Conectarse al Contenedor

```bash
docker exec -it postgres-dbt psql -U dbt_user -d dbt_database
```

Una vez dentro de `psql`, podrás crear tablas y ejecutar consultas.

---

### 3. Crear Tablas de Origen

Dentro de `psql`, define las tablas de datos crudos (Bronze Layer):

```sql
CREATE TABLE IF NOT EXISTS raw_customers (
    customer_id SERIAL PRIMARY KEY,
    customer_name TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS raw_sales (
    sale_id SERIAL PRIMARY KEY,
    customer_id INT,
    sale_amount DECIMAL(10, 2),
    sale_date TIMESTAMP
);
```

Estas tablas representan la **capa Bronze** en la arquitectura medallion, donde ingresan los datos sin transformación.

---

### 4. Poblar las Tablas con 100 Registros

#### 4.1 Cargar Clientes

```sql
DO $$
BEGIN
    FOR i IN 1..100 LOOP
        INSERT INTO raw_customers (customer_name, email)
        VALUES (
            'Customer ' || i,
            'customer' || i || '@example.com'
        );
    END LOOP;
END $$;
```

Generamos 100 clientes con nombres y correos únicos.

#### 4.2 Cargar Ventas

```sql
DO $$
BEGIN
    FOR i IN 1..100 LOOP
        INSERT INTO raw_sales (customer_id, sale_amount, sale_date)
        VALUES (
            (SELECT customer_id FROM raw_customers ORDER BY RANDOM() LIMIT 1),
            TRUNC((RANDOM() * 1000)::NUMERIC, 2),
            NOW() - (INTERVAL '1 day' * FLOOR(RANDOM() * 30))
        );
    END LOOP;
END $$;
```

Generamos 100 ventas, asignadas a clientes aleatorios y con montos y fechas simuladas.

---

### 5. Validar la Carga de Datos

Para confirmar que se insertaron 100 registros en cada tabla:
```sql
SELECT COUNT(*) FROM raw_customers;
SELECT COUNT(*) FROM raw_sales;
```

---

## dbt: Ejecutar Transformaciones y Documentación

Una vez que las tablas de origen están listas, puedes utilizar **dbt** para orquestar tu arquitectura Medallion:  
- **Bronze**: Capa de ingesta sin modificar  
- **Silver**: Capa de limpieza y estandarización  
- **Gold**: Capa de métricas y datos listos para análisis

### Comandos Básicos

- `dbt run`  
  Ejecuta los modelos y aplica las transformaciones definidas en tu proyecto (por ejemplo, para las capas Silver y Gold).

- `dbt test`  
  Verifica la calidad de tus datos con pruebas definidas en los archivos `.yml`.

- `dbt docs generate`  
  Genera la documentación del proyecto, incluyendo el diagrama de dependencias (lineage).

- `dbt docs serve`  
  Levanta un servidor local para explorar tu documentación en el navegador.

---

### Recursos Adicionales

- **[Documentación Oficial de dbt](https://docs.getdbt.com/docs/introduction)**: La referencia más completa para empezar o profundizar en dbt.  
- **[Discourse de dbt](https://discourse.getdbt.com/)**: Foro de preguntas y respuestas.  
- **[Canal de Slack](https://community.getdbt.com/)**: Comunidad en tiempo real para resolver dudas y compartir experiencias.  
- **[Eventos dbt](https://events.getdbt.com)**: Descubre conferencias y meetups para conectarte con otros usuarios de dbt.  
- **[Blog de dbt](https://blog.getdbt.com/)**: Artículos y noticias sobre el desarrollo y mejores prácticas de dbt.

---

¡Listo! Con este setup, podrás crear tu arquitectura Medallion (Bronze, Silver y Gold) y disfrutar de transformaciones ordenadas, datos consistentes y métricas confiables. ¡Feliz modelado con dbt!