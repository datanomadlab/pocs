SELECT tipo_pago, count(*) AS viajes, round(avg(propina / tarifa) * 100, 2) AS propina_pct
FROM {tabla}
WHERE tarifa > 0
GROUP BY 1
ORDER BY 2 DESC
