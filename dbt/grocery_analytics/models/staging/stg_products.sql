WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_products') }}
),

cleaned AS (
    SELECT
        sku,
        TRIM(product_name) AS product_name,
        TRIM(department) AS department,
        TRIM(category) AS category,
        price,
        cost,
        ROUND(price - cost, 2) AS margin_dollars,
        ROUND((price - cost) / NULLIF(price, 0) * 100, 1) AS margin_percent,
        is_perishable,
        CURRENT_TIMESTAMP AS loaded_at
    FROM source
)

SELECT * FROM cleaned
