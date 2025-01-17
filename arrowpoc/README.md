### **1) Crear y manipular tablas Arrow**
**Ejemplo:**  
```python
import pyarrow as pa

# Crear una tabla Arrow
data = {
    "column1": [1, 2, 3],
    "column2": ["a", "b", "c"],
    "column3": [0.1, 0.2, 0.3]
}
table = pa.table(data)
```

**¿En qué caso de uso ayuda?**  
- **Procesamiento en memoria**: Al crear tablas directamente en Arrow, los datos se almacenan de forma columnar y optimizada, lo cual agiliza operaciones analíticas.  
- **Integración con otras herramientas**: Este formato facilita enviar estos datos a sistemas como pandas, Spark o R sin costosos copiados de memoria.  
- **Primer paso en ETL**: Útil en una pipeline donde necesites cargar datos de múltiples fuentes y guardarlos temporalmente en memoria para procesarlos.

---

### **2) Convertir entre Pandas DataFrame y Arrow Table**
**Ejemplo:**  
```python
import pandas as pd
import pyarrow as pa

# DataFrame de pandas
df = pd.DataFrame({
    "A": [10, 20, 30],
    "B": ["x", "y", "z"]
})

# Convertir DataFrame a Arrow Table
arrow_table = pa.Table.from_pandas(df)

# Convertir de Arrow Table a DataFrame
df_converted = arrow_table.to_pandas()
```

**¿En qué caso de uso ayuda?**  
- **Ciencia de datos híbrida**: Muchos científicos de datos trabajan con pandas, pero necesitan la velocidad de Arrow en ciertas transformaciones.  
- **Interoperabilidad**: Facilita integrar librerías que usan Arrow internamente (por ejemplo, libraries de machine learning que se benefician de la estructura columnar) y luego volver a pandas para análisis más tradicionales.  
- **Optimización de pipelines**: Al pasar datos a Arrow y luego regresar a pandas solo cuando es necesario, se optimiza el uso de memoria y se evitan cuellos de botella.

---

### **3) Serialización con Arrow IPC (Inter-Process Communication)**
**Ejemplo:**  
```python
import pyarrow as pa

# Crear una tabla Arrow
data = {
    "name": ["Alice", "Bob"],
    "age": [25, 30]
}
table = pa.table(data)

# Serializar la tabla a un archivo
with pa.OSFile("example.arrow", "wb") as sink:
    writer = pa.ipc.new_file(sink, table.schema)
    writer.write(table)
    writer.close()

# Leer la tabla serializada
with pa.memory_map("example.arrow", "rb") as source:
    loaded_table = pa.ipc.open_file(source).read_all()
```

**¿En qué caso de uso ayuda?**  
- **Intercambio de datos entre procesos**: Es común tener múltiples procesos o servicios que deben compartir datos sin overhead de parseo/serialización (ej: JSON, CSV).  
- **Velocidad y eficiencia**: Este formato binario optimizado reduce los tiempos de lectura/escritura y el tamaño en disco.  
- **Aplicaciones distribuidas**: Ideal cuando distintas partes de un sistema necesitan acceder a los mismos datos de forma ultrarrápida.

---

### **4) Usar Apache Arrow con Parquet**
**Ejemplo:**  
```python
import pyarrow as pa
import pyarrow.parquet as pq

# Crear una tabla Arrow
data = {
    "id": [1, 2, 3],
    "value": [0.5, 0.75, 0.9]
}
table = pa.table(data)

# Escribir la tabla en un archivo Parquet
pq.write_table(table, "example.parquet")

# Leer el archivo Parquet
loaded_table = pq.read_table("example.parquet")
```

**¿En qué caso de uso ayuda?**  
- **Lakes y warehouses**: Parquet es el estándar de facto para almacenar datos en data lakes (S3, HDFS...).  
- **Escenarios de Big Data**: Combina la eficiencia columnar de Arrow en memoria con la persistencia columnar de Parquet en disco.  
- **Compatibilidad**: Herramientas como Spark, Hive o incluso DuckDB soportan Parquet; usar Arrow para leer/escribir este formato te brinda alta interoperabilidad.

---

### **5) Operaciones de fragmentación y filtro con Arrow Arrays**
**Ejemplo:**  
```python
import pyarrow as pa

# Crear un Arrow Array
array = pa.array([1, 2, 3, 4, 5])

# Filtrar el array
mask = pa.array([True, False, True, False, True])
filtered_array = array.filter(mask)
```

**¿En qué caso de uso ayuda?**  
- **Preprocesamiento y ETL**: Filtrar arrays inmensos en memoria de forma muy rápida y sin overhead.  
- **Análisis en tiempo real**: Cuando requieres filtrar datos en flujos de eventos (ej.: IoT, logs), Arrow te ayuda a manipular millones de registros en memoria con eficiencia.  
- **Construir transformaciones avanzadas**: Filtrar es solo el principio; Arrow ofrece muchas más funciones de `compute` para transformar datos (ej. agregaciones, uniones, etc.).

---

### **Extras: Arrow con Iceberg y casos financieros**
1. **Arrow con Iceberg**: Representa cómo procesar grandes volúmenes de datos en un **Data Lake** moderno, donde **Iceberg** gestiona el almacenamiento de tablas y versiones, mientras Arrow acelera la lectura y el procesamiento en memoria.  
2. **Caso Financiero**: Ilustra un **pipeline analítico** donde, tras cargar los datos en Arrow, se calculan métricas (sumas, promedios) y luego se guardan en Parquet, permitiendo consultas rápidas y una persistencia eficiente en disco.

---

## **Conclusión: Apache Arrow como “enabler” del rendimiento**
Las distintas demostraciones de uso de Arrow se enfocan en **diferentes problemáticas** de la ingeniería y la ciencia de datos:  
- Intercambio de datos rápido entre procesos,  
- Conexión con pandas,  
- Almacenamiento y filtrado eficientes,  
- Integración con formatos y sistemas ampliamente usados (Parquet, Iceberg, etc.).

Estos ejemplos reflejan situaciones típicas de la industria en las que **el performance y la interoperabilidad** son claves para el éxito de un proyecto. Desde proyectos de data science hasta arquitecturas de big data en la nube, Apache Arrow **no viene a reemplazar** herramientas como DuckDB o Spark, sino a **complementarlas** con un formato estándar y optimizado que facilita la vida de los profesionales de datos.
