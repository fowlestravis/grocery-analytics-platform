{{
    config(
        materialized='table',
        tags=['analytics', 'elasticity']
    )
}}

-- This mart prepares data for elasticity analysis and validation
WITH daily_sales AS (
    SELECT * FROM {{ ref('fct_synthetic_daily_sales') }}
),

product_aggregates AS (
    SELECT
        upc,
        category,
        subcategory,
        organic_type,
        elasticity_category,
        
        -- Ground truth
        AVG(true_elasticity) AS true_elasticity,
        AVG(base_price) AS base_price,
        
        -- Volume metrics
        COUNT(DISTINCT transaction_date) AS days_sold,
        SUM(units_sold) AS total_units_sold,
        AVG(units_sold) AS avg_daily_units,
        
        -- Price metrics (needed for elasticity estimation)
        AVG(price) AS avg_price,
        STDDEV(price) AS price_stddev,
        MIN(price) AS min_price,
        MAX(price) AS max_price,
        
        -- Promotional metrics
        SUM(CASE WHEN promotion_flag THEN 1 ELSE 0 END)::FLOAT / 
            NULLIF(COUNT(*), 0) AS promo_frequency,
        
        AVG(CASE WHEN promotion_flag THEN units_sold END) AS avg_promo_units,
        AVG(CASE WHEN NOT promotion_flag THEN units_sold END) AS avg_regular_units,
        
        AVG(CASE WHEN promotion_flag THEN price END) AS avg_promo_price,
        AVG(CASE WHEN NOT promotion_flag THEN price END) AS avg_regular_price
        
    FROM daily_sales
    GROUP BY 1, 2, 3, 4, 5
)

SELECT
    *,
    
    -- Derived metrics
    ROUND((price_stddev / NULLIF(avg_price, 0))::numeric, 4) AS price_coefficient_variation,
    ROUND(((max_price - min_price) / NULLIF(avg_price, 0))::numeric, 4) AS price_range_pct,
    ROUND(((avg_promo_units - avg_regular_units) / NULLIF(avg_regular_units, 0))::numeric, 4) AS promo_lift,
    ROUND(((avg_regular_price - avg_promo_price) / NULLIF(avg_regular_price, 0))::numeric, 4) AS avg_discount_pct,
    
    -- Data quality flags
    CASE 
        WHEN days_sold >= 100 AND price_stddev > 0 THEN 'Sufficient Data'
        WHEN days_sold < 100 THEN 'Insufficient Observations'
        WHEN price_stddev = 0 THEN 'No Price Variation'
        ELSE 'Check Data'
    END AS data_quality_flag

FROM product_aggregates
WHERE days_sold >= 50  -- Only include products with sufficient history
