-- Facturas anuladas y el monto que devolvieron, por mes.
SELECT date_trunc('month', f.fecha)::DATE AS mes,
       count(DISTINCT f.id_factura) FILTER (WHERE f.anulada) AS facturas_anuladas,
       count(DISTINCT f.id_factura) AS facturas,
       round(-sum(l.cantidad * l.precio_unitario) FILTER (WHERE f.anulada), 2) AS monto_anulado
FROM facturas f JOIN lineas l USING (id_factura)
GROUP BY mes
ORDER BY mes
