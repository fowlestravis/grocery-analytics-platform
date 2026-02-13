{{
    config(
        materialized='table',
        tags=['dimension', 'synthetic']
    )
}}

WITH stores AS (
    SELECT * FROM {{ source('synthetic_grocery', 'synthetic_stores') }}
)

SELECT
    store_id,
    store_name,
    city,
    state,
    region,
    sqft,
    volume_index,
    
    -- Classifications
    CASE
        WHEN sqft < 35000 THEN 'Small'
        WHEN sqft BETWEEN 35000 AND 44999 THEN 'Medium'
        WHEN sqft >= 45000 THEN 'Large'
    END AS store_size,
    
    CASE
        WHEN volume_index < 1.0 THEN 'Below Average'
        WHEN volume_index = 1.0 THEN 'Average'
        WHEN volume_index BETWEEN 1.0 AND 1.3 THEN 'Above Average'
        WHEN volume_index >= 1.3 THEN 'High Volume'
    END AS volume_tier

FROM stores
