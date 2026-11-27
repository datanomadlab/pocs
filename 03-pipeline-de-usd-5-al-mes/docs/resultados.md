# Resultados

> Archivo generado por `make demo`. No lo edites a mano: vuelve a correr la demo.

- **Máquina:** Darwin 25.6.0, Apple M4 Pro, 14 núcleos. Cada job corre en un contenedor limitado a 1 vCPU y 512 MB, sin disco propio.
- **Versiones:** dlt 1.32.0, DuckDB 2.0.1, PostgreSQL 18.7, psycopg2 2.9.13, PyArrow 26.0.1, Python 3.12.15, Docker 29.9.3.
- **Fecha de la medición:** 2026-11-27.
- **Datos:** Online Retail II (UCI, CC BY 4.0). 1.067.371 líneas en el archivo; se descartan repetidas entre las dos hojas: 22.523; ajustes contables (facturas A): 6; movimientos de bodega (cantidad negativa sin anulación): 3.393. Quedan 1.041.449. La historia llega hasta el 2010-11-30 y se simulan 30 días con ventas, del 2010-12-01 al 2011-01-14.

## Las siete pruebas (medido)

| # | Prueba | dlt + DuckDB | Script a mano |
|---|---|---|---|
| 1 | Carga incremental | **pasa**: movió justo lo nuevo o cambiado en 30 de 30 días; mismas filas, fechas y montos que el origen en 30 de 30 | **no pasa**: copia las tablas completas cada día (596.130 filas al final); mismas filas, fechas y montos que el origen en 30 de 30 |
| 2 | Repetir no duplica | **pasa**: movió 0 filas y el destino quedó igual | **pasa**: volvió a copiar las 596.130 y el destino quedó igual |
| 3 | Corte a medio camino | **pasa**: 3 de 3 cortes: la corrida siguiente dejó el destino igual al origen; mientras tanto, los reportes de ayer siguieron publicados en 3 de 3 | **pasa**: se recupera en la corrida siguiente; hasta entonces lineas.csv quedó con entre 26 % y 37 % de las líneas |
| 4 | Columna nueva en el origen | **no pasa**: la columna llegó con 3 de sus 4.453 valores: las filas viejas no cambian de fecha y la carga por fecha de actualización no las vuelve a leer | **pasa**: la columna llegó con 4.453 de sus 4.453 valores |
| 5 | Dato malo | **pasa con código propio**: detuvo la publicación y dejó la de ayer; corregido el dato, la corrida siguiente publicó. Lo hacen 25 líneas de Python del job | **no pasa**: copió el precio negativo y terminó bien (código 0): nadie se entera |
| 6 | Borrado en el origen | **no pasa**: la línea borrada sigue en el destino: la carga por fecha de actualización no ve lo que ya no está | **pasa**: la recarga completa la saca |
| 7 | Rastro de cada corrida | **pasa con código propio**: 39 de 39 corridas terminadas con filas, segundos y resultado; las 3 cortadas salieron con código 137. Lo escribe el job | **no pasa**: no deja nada más que los CSV: ni filas ni tiempos. Cortado, sí sale con error (137) |

- Si las vistas leyeran solo las cargas que dlt registró en `_dlt_loads`, el corte entre guardar el avance y registrar la carga escondería para siempre 1.500 filas: la corrida siguiente cree que ya las cargó.
- El dato malo lo detectó la prueba precios_negativos.

## Las corridas (medido)

| | dlt + DuckDB | Script a mano |
|---|---|---|
| Carga inicial (un año de historia) | 2,9 s | 0,3 s |
| Corrida diaria, mediana | 2,3 s | 0,3 s |
| Corrida diaria, peor día | 2,4 s | 0,4 s |
| Filas movidas por corrida, mediana | 2.236 | 574.556 |
| Memoria máxima, corridas diarias | 278 MB de 512 | sin medir |
| Destino después de los días simulados | 8 MB en 373 archivos | 30 MB en 4 archivos |
| Código que hay que mantener | 104 líneas | 16 líneas |

Los reportes son 5 consultas SQL (51 líneas) que corren solo en el camino de dlt; el script no los tiene. Las líneas no cuentan vacías ni comentarios, ni el Dockerfile, que es el mismo para los dos, ni la configuración del despliegue (job, programador, permisos y clave de la base), que todavía no existe.

## Costo mensual

Cada celda: sin capa gratuita / con capa gratuita. La primera fila de la primera columna es **estimada** (segundos medidos por precios publicados); el resto es **modelo**.

| Escenario | dlt + DuckDB en Cloud Run | Fivetran + BigQuery | Airbyte + BigQuery |
|---|---|---|---|
| La tienda del dataset: los datos medidos, una corrida al día | USD 0,16 / USD 0 | USD 36 / USD 0 | USD 20 / USD 20 |
| 10 veces más ventas: una tienda con 10 veces más facturas | USD 0,16 / USD 0 | USD 318 / USD 318 | USD 20 / USD 20 |
| 100 veces más ventas: una tienda con 100 veces más facturas | USD 0,20 / USD 0 | USD 1.149 / USD 1.145 | USD 24 / USD 20 |

Desglose de la primera fila: 2,3 s por corrida más 10 s de arranque, cobrados como un minuto:

| Parte | Sin capa gratuita | Con capa gratuita |
|---|---|---|
| Cloud Run (el job) | USD 0,03 | USD 0 |
| Cloud Scheduler (el disparo diario) | USD 0,10 | USD 0 |
| Cloud Storage (el destino y sus operaciones) | menos de USD 0,01 | USD 0 |
| Artifact Registry (la imagen) | USD 0,01 | USD 0 |
| **Total** | **USD 0,16** | **USD 0** |

- Con 100 veces más ventas la corrida duraría 96,4 s y seguiría lejos de USD 5. Lo que no está medido es si cabe en 512 MB: el costo no es lo primero que se rompe.
- Fivetran deja el plan gratuito desde 8 veces los datos medidos: 63.229 filas activas en los 30 días con ventas simulados (medido en el origen). Esos días ocupan 45 días de calendario, así que la cifra sobrestima un mes.

## Entradas del modelo (medido)

Lo que el modelo toma de la medición, para rehacer la cuenta con otros precios:

| Entrada | Valor |
|---|---|
| Arranque del contenedor y de Python, mediana | 1,4 s |
| Carga de dlt por corrida, mediana | 0,3 s |
| Pruebas de datos y reportes por corrida, mediana | 0,6 s |
| Archivos que escribe cada corrida, mediana | 12 |
| Parquet crudos que lee cada corrida al final del mes | 122 |
| Destino de dlt al final del mes | 8 MB |
| Imagen del job, comprimida | 155 MB |
| Filas distintas que cambiaron en los días simulados | 63.229 |
| Lo que pesan esas filas en Postgres | 5 MB |
| Lo que pesan las cuatro tablas en Postgres | 46 MB |

## Supuestos

- **El más fuerte:** cargar y publicar crecen en proporción a los datos y la corrida sigue cabiendo en 1 vCPU y 512 MB. Con los datos medidos usa 278 MB; con 10 o 100 veces más no está medido.
- El job llega a Postgres por internet, con usuario y clave. Si la base solo acepta direcciones conocidas, hace falta una IP de salida fija para Cloud Run, que no está en el modelo y puede costar más que todo lo demás.
- El bucket se monta como carpeta del contenedor (Cloud Storage FUSE), sin costo aparte. No está probado.
- Los montos son infraestructura: no incluyen las horas de quien opera, ni alertas.
- Cloud Run tarda 10 s en partir el contenedor (no medido). Con un minuto mínimo por corrida, cambia poco.
- Fivetran cobra las filas distintas que cambiaron en el mes; Airbyte, el volumen serializado, que aquí se supone 2 veces lo que pesan en Postgres.
- BigQuery almacena lo que pesan las tablas en Postgres y cada reporte lee las tablas completas.
- Precios de lista en us-central1, revisados el 26 de noviembre de 2026. Todo está en `escenario.toml`.
