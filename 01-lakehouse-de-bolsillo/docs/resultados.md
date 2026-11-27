# Resultados · Experimento 01

> Archivo generado por `make demo`. No lo edites a mano: vuelve a correr la demo.

- **Datos:** NYC TLC, taxis amarillos, meses 2024-01, 2024-02, 2024-03 (9.554.722 viajes).
- **Máquina:** Darwin 25.6.0, Apple M4 Pro, 14 núcleos. DuckDB limitado a 4 hilos y 8 GB para parecerse a un contenedor chico.
- **Versiones:** DuckDB 2.0.0, PyIceberg 0.12.0.
- **Fecha de la medición:** 2026-11-19.

## Por consulta

DuckDB está **medido** en esta máquina, leyendo la tabla Iceberg desde disco local (no desde un bucket). BigQuery está **estimado** con las reglas públicas de cobro por demanda: bytes lógicos de las columnas que toca la consulta.

| Consulta | DuckDB en frío | DuckDB mediana | BigQuery: bytes estimados | BigQuery: USD por corrida |
|---|---|---|---|---|
| Viajes e ingresos por mes | 73 ms | 69 ms | 152,9 MB | 0,000869 |
| Propina promedio según medio de pago | 42 ms | 42 ms | 229,3 MB | 0,001303 |
| Las 10 zonas de origen con más ingresos | 22 ms | 21 ms | 152,9 MB | 0,000869 |
| Viajes por hora en un solo mes (poda de particiones) | 24 ms | 24 ms | 47,4 MB | 0,00027 |
| Duración p50 y p95 por día de la semana | 173 ms | 168 ms | 152,9 MB | 0,000869 |

BigQuery todavía no está medido. Corre `make bq` con una cuenta propia de GCP para agregar los bytes facturados y los tiempos reales.

## BigQuery simulado

Esto es una **simulación**, sin cuenta de GCP. Cada `sql/bigquery/*.sql` se leyó con el analizador de dialecto BigQuery de sqlglot 30.33.0, se tradujo a DuckDB y se corrió sobre la misma tabla. Comprueba que el SQL es válido, que da lo mismo que la versión DuckDB y qué columnas y particiones leería BigQuery. **No** mide sus tiempos ni sus bytes facturados.

| Consulta | SQL válido y mismo resultado | Columnas que lee | Poda particiones | Bytes según el SQL (simulado) | Coincide con la estimación |
|---|---|---|---|---|---|
| Viajes e ingresos por mes | sí | inicio, total | no | 152,9 MB | sí |
| Propina promedio según medio de pago | sí | propina, tarifa, tipo_pago | no | 229,3 MB | sí |
| Las 10 zonas de origen con más ingresos | sí | total, zona_origen | no | 152,9 MB | sí |
| Viajes por hora en un solo mes (poda de particiones) | sí | distancia_millas, inicio | sí | 47,4 MB | sí |
| Duración p50 y p95 por día de la semana | sí, a 0,3 % | fin, inicio | no | 152,9 MB | sí |

La diferencia permitida es 1 %: BigQuery calcula los percentiles con `APPROX_QUANTILES`, que es aproximado, y DuckDB con `quantile_cont`, que es exacto.

## Almacenamiento

| | Tamaño |
|---|---|
| Parquet de origen (descarga) | 160,4 MB |
| Tabla Iceberg (Parquet comprimido + metadatos) | 164,3 MB |
| Lo que BigQuery cobraría como almacenamiento lógico (estimado) | 1.378,2 MB |

## Costo mensual por escenario (modelo)

Esto es un **modelo**, no una factura. Una ejecución son las 5 consultas una vez. Los supuestos están en `escenario.toml` y se listan abajo.

| Escenario | BigQuery (USD/mes) | Lakehouse (USD/mes) | Ahorro | BigQuery sin capa gratuita | Lakehouse sin capa gratuita | Ahorro sin capa gratuita |
|---|---|---|---|---|---|---|
| **De bolsillo**: los datos medidos, dashboard que se refresca cada hora | 0 | 0,003286 | no hay costo que ahorrar | 3,04 | 0,87 | 71 % |
| **Equipo chico**: 100 veces más datos, refresco cada 15 minutos | 1.199,99 | 9,59 | 99 % | 1.206,44 | 14,81 | 99 % |
| **Empresa mediana**: 1.000 veces más datos, refresco cada 15 minutos | 12.057,95 | 112,81 | 99 % | 12.064,40 | 118,03 | 99 % |

### Supuestos del modelo

- Precios (revisar en la fuente antes de publicar): BigQuery por demanda USD 6,25 por TiB, con 1 TiB gratis al mes; almacenamiento lógico activo USD 0,02 por GiB al mes, con 10 GiB gratis; bucket USD 0,02 por GB al mes; contenedor USD 0,000024 por vCPU-segundo y USD 0,0000025 por GiB-segundo.
- El lado lakehouse corre en un contenedor de 4 vCPU y 8 GiB que se paga solo mientras corre. Cada ejecución suma 10 s de arranque y latencia del bucket: ese número es un supuesto, no una medición.
- Los tiempos de DuckDB vienen de un Mac con disco local. Un núcleo de Apple Silicon no es un vCPU de la nube, y leer de un bucket es más lento que leer de disco.
- Al multiplicar los datos, los bytes escaneados y el tiempo de DuckDB crecen en la misma proporción. Para 1.000 veces más datos, eso es optimista para un solo nodo.
- No incluye: operaciones ni tráfico de salida del bucket, el costo de mantener la tabla (compactación, limpieza de snapshots) ni las horas de quien la opera.
- BigQuery se modela por demanda y sin caché: cada ejecución vuelve a escanear, como pasa cuando los datos cambian entre un refresco y otro. Con caché de resultados, vistas materializadas o reservas (slots) la cuenta de BigQuery baja.
