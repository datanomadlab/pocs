-- Lo que la empresa mira cada mañana: facturas, unidades e ingresos de cada día, sin anulaciones.
SELECT CAST(f.fecha AS DATE) AS dia,
       count(DISTINCT f.id_factura) AS facturas,
       sum(l.cantidad) AS unidades,
       round(sum(l.cantidad * l.precio_unitario), 2) AS ingresos
FROM facturas f JOIN lineas l USING (id_factura)
WHERE NOT f.anulada
GROUP BY dia
ORDER BY dia
