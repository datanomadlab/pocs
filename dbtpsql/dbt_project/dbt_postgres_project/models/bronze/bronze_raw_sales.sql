{{ config(materialized='incremental') }}

SELECT
    sale_id,
    customer_id,
    sale_amount,
    sale_date
FROM {{ source('source_data', 'raw_sales') }}
{% if is_incremental() %}
WHERE sale_date > (SELECT COALESCE(MAX(sale_date), '1900-01-01'::DATE) FROM {{ this }})
{% endif %}
