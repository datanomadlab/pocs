SELECT hour(inicio) AS hora, count(*) AS viajes, round(avg(distancia_millas), 2) AS millas_promedio
FROM {tabla}
WHERE inicio >= TIMESTAMP '{mes_inicio}' AND inicio < TIMESTAMP '{mes_fin}'
GROUP BY 1
ORDER BY 1
