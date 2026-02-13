SELECT
    sku AS product_key,
    sku,
    product_name,
    department,
    category,
    price AS current_price,
    cost AS current_cost,
    margin_dollars,
    margin_percent,
    is_perishable,
    loaded_at AS effective_date
FROM {{ ref('stg_products') }}
