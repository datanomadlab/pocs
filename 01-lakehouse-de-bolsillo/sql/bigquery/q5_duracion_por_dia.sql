-- APPROX_QUANTILES es aproximado; DuckDB usa quantile_cont (exacto). Los percentiles pueden diferir un poco.
SELECT EXTRACT(DAYOFWEEK FROM inicio) - 1 AS dia_semana,
       ROUND(APPROX_QUANTILES(DATETIME_DIFF(fin, inicio, SECOND) / 60.0, 100)[OFFSET(50)], 2) AS minutos_p50,
       ROUND(APPROX_QUANTILES(DATETIME_DIFF(fin, inicio, SECOND) / 60.0, 100)[OFFSET(95)], 2) AS minutos_p95
FROM {tabla}
GROUP BY 1
ORDER BY 1
