-- Los 100 productos que más ingresos dejaron, con su descripción y precio de lista vigentes.
SELECT l.codigo,
       p.descripcion,
       p.precio AS precio_de_lista,
       sum(l.cantidad) AS unidades,
       round(sum(l.cantidad * l.precio_unitario), 2) AS ingresos
FROM lineas l
JOIN facturas f USING (id_factura)
LEFT JOIN productos p USING (codigo)
WHERE NOT f.anulada
GROUP BY l.codigo, p.descripcion, p.precio
ORDER BY ingresos DESC
LIMIT 100
