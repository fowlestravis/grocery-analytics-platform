SELECT
    store_id AS store_key,
    store_id,
    store_name,
    city,
    state,
    store_format,
    square_footage,
    opened_date,
    CASE 
        WHEN store_format = 'Large Format' THEN 'Large'
        WHEN store_format = 'Neighborhood Market' THEN 'Medium'
        ELSE 'Small'
    END AS store_size_category,
    loaded_at
FROM {{ ref('stg_stores') }}
