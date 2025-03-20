# Búsqueda Semántica de Productos con PostgreSQL y pgvector

Este proyecto implementa un sistema de búsqueda semántica para productos electrónicos utilizando PostgreSQL con la extensión pgvector y embeddings de texto.

## Dataset
El dataset utilizado contiene información de productos electrónicos de Amazon (10,000 items) y puede ser descargado desde:
https://www.kaggle.com/datasets/akeshkumarhp/electronics-products-amazon-10k-items

## Requisitos

### Software
- Docker y Docker Compose
- Python 3.x
- PostgreSQL con extensión pgvector

### Dependencias de Python
```bash
pip install -r requirements.txt
```

## Estructura del Proyecto

- `docker-compose.yml`: Configuración del contenedor PostgreSQL con pgvector
- `init.sql`: Script de inicialización de la base de datos
- `example.py`: POC básica de pgvector con datos sintéticos
- `example2.py`: Implementación completa con datos reales de Amazon

## Configuración

1. Iniciar el contenedor PostgreSQL:
```bash
docker-compose up -d
```

2. Asegurarse de que el archivo `dataset.csv` esté en el directorio raíz

3. Ejecutar el script de búsqueda semántica:
```bash
python example2.py
```

## Funcionalidades

- Limpieza y normalización de datos (precios, ratings, números)
- Generación de embeddings usando SentenceTransformer
- Búsqueda semántica por similitud de vectores
- Indexación eficiente con IVFFLAT

## Ejemplos de Uso

El script incluye dos ejemplos de búsqueda:
1. Productos de tecnología y gadgets innovadores
2. Libros de ciencia ficción

Los resultados muestran los productos más relevantes ordenados por similitud semántica.

## Estructura de la Base de Datos

Tabla `products`:
- id: SERIAL PRIMARY KEY
- name: TEXT
- main_category: TEXT
- sub_category: TEXT
- image: TEXT
- link: TEXT
- ratings: FLOAT
- no_of_ratings: INTEGER
- discount_price: FLOAT
- actual_price: FLOAT
- embedding: VECTOR(384)

## Notas
- Los embeddings se generan utilizando el modelo 'all-MiniLM-L6-v2'
- La dimensión del vector de embeddings es 384
- Se utiliza el operador <=> para calcular la similitud coseno entre vectores