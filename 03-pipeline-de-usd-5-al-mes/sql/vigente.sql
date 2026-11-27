-- La versión vigente de cada fila de {tabla}. Sobre archivos Parquet sueltos dlt solo agrega: una fila
-- que cambió llega otra vez, y una carga cortada puede dejar archivos que la siguiente repite.
-- Por eso de cada llave queda una sola fila, la más nueva.
-- No se filtra por _dlt_loads: al cerrar una carga dlt guarda primero el avance y después ese registro,
-- y un corte entre ambos dejaría filas ya cargadas que nunca se volverían a leer ni a mostrar.
CREATE OR REPLACE VIEW {tabla} AS
SELECT * EXCLUDE (filename)
FROM read_parquet('{crudo}/{tabla}/*.parquet', union_by_name = true, filename = true)
QUALIFY row_number() OVER (PARTITION BY {llave} ORDER BY actualizado_en DESC, filename DESC) = 1
