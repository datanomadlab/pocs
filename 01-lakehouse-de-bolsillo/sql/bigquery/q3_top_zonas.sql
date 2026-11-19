SELECT zona_origen, COUNT(*) AS viajes, ROUND(SUM(total), 2) AS ingresos
FROM {tabla}
GROUP BY 1
ORDER BY 3 DESC
LIMIT 10
