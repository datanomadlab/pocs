SELECT zona_origen, count(*) AS viajes, round(sum(total), 2) AS ingresos
FROM {tabla}
GROUP BY 1
ORDER BY 3 DESC
LIMIT 10
