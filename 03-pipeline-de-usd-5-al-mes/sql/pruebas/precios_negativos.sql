-- Ninguna línea puede tener precio negativo. Cada fila que devuelve esta consulta es un error.
SELECT id_linea, id_factura, precio_unitario FROM lineas WHERE precio_unitario < 0
