-- Toda línea pertenece a una factura que existe.
SELECT l.id_linea, l.id_factura
FROM lineas l LEFT JOIN facturas f USING (id_factura)
WHERE f.id_factura IS NULL
