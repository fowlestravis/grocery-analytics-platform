{{
    config(
        materialized='table',
        tags=['fact', 'synthetic']
    )
}}

WITH transactions AS (
    SELECT * FROM {{ ref('stg_synthetic_transactions') }}
),

products AS (
    SELECT * FROM {{ ref('dim_synthetic_products') }}
),

stores AS (
    SELECT * FROM {{ ref('dim_synthetic_stores') }}
)

SELECT
    -- Keys
    t.transaction_date,
    t.store_id,
    t.upc,
    
    -- Dimension attributes (for filtering without joins)
    s.region,
    s.city,
    s.state,
    s.store_size,
    s.volume_tier,
    p.category,
    p.subcategory,
    p.family,
    p.organic_type,
    p.price_tier,
    p.elasticity_category,
    p.seasonality,
    
    -- Date attributes
    t.year,
    t.month,
    t.quarter,
    t.day_of_week,
    t.day_name,
    t.is_weekend,
    
    -- Metrics
    t.units_sold,
    t.gross_sales,
    t.cost,
    t.margin,
    t.price,
    t.promotion_flag,
    t.margin_pct,
    
    -- For elasticity validation
    p.true_elasticity,
    p.base_price,
ROUND((t.price / NULLIF(p.base_price, 0))::numeric, 4) AS price_index,
ROUND(((t.price - p.base_price) / NULLIF(p.base_price, 0))::numeric, 4) AS price_variance_pct

FROM transactions t
LEFT JOIN products p ON t.upc = p.upc
LEFT JOIN stores s ON t.store_id = s.store_id
