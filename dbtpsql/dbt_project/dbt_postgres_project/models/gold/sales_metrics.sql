{{ config(
    materialized='incremental',
    unique_key='customer_id'
) }}

WITH latest_date AS (
    {% if is_incremental() %}
    SELECT COALESCE(MAX(updated_at), '1900-01-01'::TIMESTAMP) AS max_date
    FROM {{ this }}
    {% else %}
    SELECT '1900-01-01'::TIMESTAMP AS max_date
    {% endif %}
),
customer_metrics AS (
    SELECT 
        customer_id,
        COUNT(*) as total_sales,
        SUM(sale_amount) as total_amount,
        AVG(sale_amount) as avg_amount,
        MIN(updated_at) as first_purchase_date,  -- Cambiado de created_at a updated_at
        MAX(updated_at) as last_purchase_date,   -- Cambiado de created_at a updated_at
        CURRENT_TIMESTAMP as processed_at
    FROM {{ ref('cleaned_sales') }}
    WHERE updated_at > (SELECT max_date FROM latest_date)  -- Cambiado de created_at a updated_at
    GROUP BY customer_id
)
SELECT 
    customer_id,
    total_sales,
    total_amount,
    avg_amount,
    first_purchase_date,
    last_purchase_date,
    processed_at
FROM customer_metrics