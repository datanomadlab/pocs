SELECT DATETIME_TRUNC(inicio, MONTH) AS mes, COUNT(*) AS viajes, ROUND(SUM(total), 2) AS ingresos
FROM {tabla}
GROUP BY 1
ORDER BY 1
