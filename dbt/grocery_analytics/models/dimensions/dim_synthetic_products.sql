{{
    config(
        materialized='table',
        tags=['dimension', 'synthetic']
    )
}}

WITH products AS (
    SELECT * FROM {{ source('synthetic_grocery', 'synthetic_products') }}
)

SELECT
    upc,
    product_name,
    category,
    subcategory,
    family,
    organic,
    true_elasticity,
    base_price,
    base_cost,
    seasonality,
    promotion_frequency,
    
    -- Calculated attributes
    ROUND(((base_price - base_cost) / NULLIF(base_price, 0))::numeric, 4) AS base_margin_pct,
    ROUND((base_price - base_cost)::numeric, 2) AS base_margin_dollars,
    
    -- Classifications
    CASE
        WHEN organic = TRUE THEN 'Organic'
        ELSE 'Conventional'
    END AS organic_type,
    
    CASE
        WHEN base_price < 2.00 THEN 'Budget'
        WHEN base_price BETWEEN 2.00 AND 4.99 THEN 'Mid-Tier'
        WHEN base_price >= 5.00 THEN 'Premium'
    END AS price_tier,
    
    CASE
        WHEN true_elasticity > -1.0 THEN 'Inelastic'
        WHEN true_elasticity BETWEEN -1.0 AND -1.5 THEN 'Unit Elastic'
        WHEN true_elasticity < -1.5 THEN 'Elastic'
    END AS elasticity_category

FROM products
