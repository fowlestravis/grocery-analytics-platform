SELECT
    f.transaction_date,
    s.store_id,
    s.store_name,
    s.store_format,
    s.store_size_category,
    s.city,
    s.state,
    COUNT(DISTINCT f.transaction_id) AS transaction_count,
    SUM(f.quantity) AS units_sold,
    SUM(f.sales_amount) AS total_sales,
    SUM(f.cost_amount) AS total_cost,
    SUM(f.margin_amount) AS total_margin,
    ROUND(SUM(f.margin_amount) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_percent,
    ROUND(SUM(f.sales_amount) / NULLIF(COUNT(DISTINCT f.transaction_id), 0), 2) AS avg_basket_size,
    d.is_weekend,
    d.is_holiday_season
FROM {{ ref('fact_sales') }} f
JOIN {{ ref('dim_store') }} s ON f.store_key = s.store_key
JOIN {{ ref('dim_date') }} d ON f.transaction_date = d.date_day
GROUP BY 
    f.transaction_date,
    s.store_id,
    s.store_name,
    s.store_format,
    s.store_size_category,
    s.city,
    s.state,
    d.is_weekend,
    d.is_holiday_season
