{{
    config(
        materialized='view',
        tags=['staging', 'synthetic']
    )
}}

WITH source AS (
    SELECT * FROM {{ source('synthetic_grocery', 'synthetic_transactions') }}
),

cleaned AS (
    SELECT
        transaction_date::date AS transaction_date,
        store_id,
        upc,
        units_sold,
        gross_sales,
        cost,
        margin,
        price,
        promotion_flag,
        
        -- Date attributes
        EXTRACT(YEAR FROM transaction_date) AS year,
        EXTRACT(MONTH FROM transaction_date) AS month,
        EXTRACT(QUARTER FROM transaction_date) AS quarter,
        EXTRACT(DOW FROM transaction_date) AS day_of_week,
        TO_CHAR(transaction_date, 'Day') AS day_name,
        
        -- Calculated metrics
        ROUND((gross_sales / NULLIF(units_sold, 0))::numeric, 2) AS avg_unit_price,
        ROUND((margin / NULLIF(gross_sales, 0))::numeric, 4) AS margin_pct,
        
        -- Flags
        CASE 
            WHEN EXTRACT(DOW FROM transaction_date) IN (0, 6) THEN TRUE 
            ELSE FALSE 
        END AS is_weekend

    FROM source
    WHERE units_sold > 0 
      AND price > 0
      AND gross_sales > 0
)

SELECT * FROM cleaned
