SELECT date_trunc('month', inicio) AS mes, count(*) AS viajes, round(sum(total), 2) AS ingresos
FROM {tabla}
GROUP BY 1
ORDER BY 1
