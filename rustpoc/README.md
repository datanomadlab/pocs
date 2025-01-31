# ETL Performance Comparison: Rust (Polars/Rayon) vs Python

![Rust vs Python](https://img.shields.io/badge/Comparison-Rust_vs_Python-blue)

Proof of Concept que compara la implementación de un flujo ETL básico en Rust (usando Polars y Rayon) contra una solución equivalente en Python (pandas).

## Estructura del Proyecto

- `rayon-etl/`: Implementación en Rust usando Rayon
- `polars-etl/`: Implementación en Rust usando Polars
- `empleados.csv`: Datos de ejemplo

## Requisitos Previos

- **Rust**: 1.70+ (instalar via [rustup](https://rustup.rs/))
- **Python**: 3.8+
- **Dependencias Python**:
  ```bash
  pip install pandas numpy
  ```

  Espacio en disco: 2GB+ (para dataset de 1GB)
- **Dependencias Ejecutables**:

  ```bash 
  cd benchmarks
  chmod +x benchmark.sh
  ./benchmark.sh
  ```

## Resultados Comparativos (1M de registros)

| Sistema          | Tiempo (s) | Memoria (MB) | CSV Size (KB) | SQLite Size (KB) |
|------------------|------------|--------------|---------------|------------------|
| **Rust (Polars)** | 2.1        | 92           | 1.8           | 12               |
| **Rust (Rayon)**  | 3.8        | 145          | 1.8           | 12               |
| Python (pandas)  | 12.5       | 510          | 1.8           | 12               |

**Notas:**
- Datos recolectados en Macbook Pro M4
- Dataset: 1,000,000 registros, 5 departamentos
- Versiones: Rust 1.72, Python 3.11, Polars 0.37, pandas 2.1.1

## Conclusión

Rust (Polars) muestra un rendimiento significativamente mejor que Rayon, especialmente en términos de memoria y tiempo de ejecución.

## Mejoras Posibles

- Añadir soporte para Parquet/JSON
- Implementar streaming para datasets >10GB
- Comparar con Apache Arrow/DuckDB
- Añadir monitorización de CPU/GPU

