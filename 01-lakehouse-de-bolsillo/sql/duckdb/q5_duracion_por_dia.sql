SELECT dayofweek(inicio) AS dia_semana,
       round(quantile_cont(date_diff('second', inicio, fin) / 60.0, 0.5), 2) AS minutos_p50,
       round(quantile_cont(date_diff('second', inicio, fin) / 60.0, 0.95), 2) AS minutos_p95
FROM {tabla}
GROUP BY 1
ORDER BY 1
