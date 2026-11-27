-- Por mes: cuántos clientes compraron, cuántos lo hacían por primera vez y cuántos volvían.
WITH compras AS (
  SELECT DISTINCT id_cliente, date_trunc('month', fecha)::DATE AS mes
  FROM facturas
  WHERE NOT anulada AND id_cliente IS NOT NULL
), primera AS (
  SELECT id_cliente, min(mes) AS primer_mes FROM compras GROUP BY id_cliente
)
SELECT c.mes,
       count(*) AS clientes,
       count(*) FILTER (WHERE c.mes = p.primer_mes) AS nuevos,
       count(*) FILTER (WHERE c.mes > p.primer_mes) AS recurrentes
FROM compras c JOIN primera p USING (id_cliente)
GROUP BY c.mes
ORDER BY c.mes
