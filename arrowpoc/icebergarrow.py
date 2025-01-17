import pyarrow as pa
import os
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField,
    LongType,
    StringType,
    DoubleType
)
from pyiceberg.io import PyArrowFileIO

# Configuración del entorno y directorios
BASE_DIR = os.path.abspath("./iceberg_poc")
WAREHOUSE_DIR = os.path.join(BASE_DIR, "warehouse")

print(f"Usando warehouse en: {WAREHOUSE_DIR}")

# Crear directorios necesarios
os.makedirs(WAREHOUSE_DIR, exist_ok=True)

# Crear datos de ejemplo usando PyArrow
data = pa.table({
    'id': pa.array([1, 2, 3, 4, 5], type=pa.int64()),
    'name': pa.array(['a', 'b', 'c', 'd', 'e'], type=pa.string()),
    'value': pa.array([10.0, 20.0, 30.0, 40.0, 50.0], type=pa.float64())
})

print("\nDatos de ejemplo creados:")
print(data.schema)
print(data.to_pandas())

try:
    # Configurar catálogo local
    catalog_properties = {
        "type": "local",
        "warehouse": WAREHOUSE_DIR,
        "uri": f"file://{WAREHOUSE_DIR}"
    }
    
    print("\nConfigurando catálogo con propiedades:", catalog_properties)
    
    catalog = load_catalog(
        "demo",
        **catalog_properties
    )

    # Definir el esquema
    schema = Schema(
        NestedField(1, "id", LongType(), required=True),
        NestedField(2, "name", StringType(), required=True),
        NestedField(3, "value", DoubleType(), required=True)
    )

    print("\nEsquema definido:", schema)

    # Crear namespace y tabla
    namespace = "default"
    table_name = f"{namespace}.example_table"
    
    print(f"\nCreando namespace '{namespace}' si no existe...")
    if namespace not in catalog.list_namespaces():
        catalog.create_namespace(namespace)

    print(f"\nCreando tabla '{table_name}'...")
    if not catalog.table_exists(table_name):
        table = catalog.create_table(
            identifier=table_name,
            schema=schema,
            properties={
                "format-version": "2",
                "write.format.default": "parquet"
            }
        )
    else:
        table = catalog.load_table(table_name)

    # Configurar PyArrow FileIO
    table.io = PyArrowFileIO()

    # Escribir datos
    print("\nEscribiendo datos...")
    table.append(data)
    print("Datos escritos exitosamente")

    # Leer datos
    print("\nLeyendo datos...")
    scanner = table.scan()
    arrow_table = scanner.to_arrow()
    print("\nDatos leídos:")
    print(arrow_table.to_pandas())

except Exception as e:
    print(f"\nError: {str(e)}")
    print("\nStacktrace:")
    import traceback
    traceback.print_exc()