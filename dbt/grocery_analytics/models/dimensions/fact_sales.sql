SELECT
    t.transaction_id,
    t.transaction_timestamp,
    t.transaction_date,
    t.store_id AS store_key,
    t.sku AS product_key,
    t.quantity,
    t.price AS unit_price,
    p.cost AS unit_cost,
    t.line_total AS sales_amount,
    ROUND(t.quantity * p.cost, 2) AS cost_amount,
    ROUND(t.line_total - (t.quantity * p.cost), 2) AS margin_amount,
    t.transaction_hour,
    t.day_of_week
FROM {{ ref('stg_transactions') }} t
LEFT JOIN {{ ref('stg_products') }} p 
    ON t.sku = p.sku
