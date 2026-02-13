SELECT
    category,

    -- Product counts
    COUNT(*) AS total_products,
    COUNT(*) FILTER (WHERE is_active) AS active_products,
    COUNT(*) FILTER (WHERE NOT is_active) AS inactive_products,

    -- Reorder metrics
    COUNT(*) FILTER (WHERE needs_reorder) AS products_needing_reorder,
    ROUND(
        COUNT(*) FILTER (WHERE needs_reorder) * 100.0 / NULLIF(COUNT(*), 0),
        1
    ) AS reorder_percentage,

    -- Stock metrics
    ROUND(AVG(stock_quantity), 1) AS avg_stock_quantity,
    SUM(stock_quantity) AS total_stock_quantity,
    ROUND(AVG(reorder_level), 1) AS avg_reorder_level,

    -- Turnover metrics
    ROUND(AVG(inventory_turnover_rate), 1) AS avg_turnover_rate,
    ROUND(AVG(turnover_percentage), 2) AS avg_turnover_percentage,

    -- Expiration metrics
    COUNT(*) FILTER (WHERE days_until_expiration <= 30 AND days_until_expiration > 0) AS products_expiring_soon,
    COUNT(*) FILTER (WHERE days_until_expiration <= 0) AS products_expired,

    -- Financial metrics
    ROUND(AVG(unit_price), 2) AS avg_unit_price,
    SUM(sales_volume) AS total_sales_volume

FROM {{ ref('stg_inventory') }}
GROUP BY category
ORDER BY category
