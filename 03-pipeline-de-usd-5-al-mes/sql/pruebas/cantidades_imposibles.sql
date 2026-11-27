-- Una cantidad negativa solo vale en una factura anulada, y ninguna línea lleva cantidad cero.
SELECT l.id_linea, l.id_factura, l.cantidad
FROM lineas l JOIN facturas f USING (id_factura)
WHERE l.cantidad = 0 OR (l.cantidad < 0 AND NOT f.anulada)
