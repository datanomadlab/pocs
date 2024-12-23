{{ config(
    materialized='table',
    schema='public',
    alias='clean'
) }}

SELECT
    id,
    nombre,
    apellido,
    TO_CHAR(fecha_registro, 'YYYY-MM-DD') AS fecha_registro,
    monto
FROM {{ source('raw_source', 'not_clean') }} 