{{ config(
    materialized='incremental',
    unique_key='sale_id'
) }}

WITH latest_date AS (
    -- Maneja la lógica incremental asegurando la existencia de la tabla
    {% if is_incremental() %}
    SELECT COALESCE(MAX(updated_at), '1900-01-01'::TIMESTAMP) AS max_updated_at
    FROM {{ this }}
    {% else %}
    SELECT '1900-01-01'::TIMESTAMP AS max_updated_at
    {% endif %}
),
filtered_sales AS (
    -- Filtrar datos nuevos desde la capa Bronze
    SELECT
        sale_id,
        customer_id,
        sale_amount,
        sale_date,
        CURRENT_TIMESTAMP AS updated_at
    FROM {{ ref('bronze_raw_sales') }}
    WHERE sale_date > (SELECT max_updated_at FROM latest_date)
),
deduplicated AS (
    -- Deduplicar: Mantener la transacción más reciente por cliente
    SELECT
        sale_id,
        customer_id,
        sale_amount,
        sale_date,
        updated_at,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY sale_date DESC) AS row_num
    FROM filtered_sales
)
SELECT
    sale_id,
    customer_id,
    sale_amount,
    sale_date,
    updated_at
FROM deduplicated
WHERE row_num = 1
