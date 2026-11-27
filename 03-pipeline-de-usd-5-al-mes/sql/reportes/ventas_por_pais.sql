-- Ingresos y clientes por país y mes. El país es el vigente del cliente; sin cliente, "sin registro".
SELECT date_trunc('month', f.fecha)::DATE AS mes,
       coalesce(c.pais, 'sin registro') AS pais,
       count(DISTINCT f.id_cliente) AS clientes,
       round(sum(l.cantidad * l.precio_unitario), 2) AS ingresos
FROM facturas f
JOIN lineas l USING (id_factura)
LEFT JOIN clientes c USING (id_cliente)
WHERE NOT f.anulada
GROUP BY mes, pais
ORDER BY mes, ingresos DESC
