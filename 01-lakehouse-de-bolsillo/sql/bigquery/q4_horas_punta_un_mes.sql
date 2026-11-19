SELECT EXTRACT(HOUR FROM inicio) AS hora, COUNT(*) AS viajes, ROUND(AVG(distancia_millas), 2) AS millas_promedio
FROM {tabla}
WHERE inicio >= DATETIME '{mes_inicio}' AND inicio < DATETIME '{mes_fin}'
GROUP BY 1
ORDER BY 1
