WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_stores') }}
),

cleaned AS (
    SELECT
        store_id,
        TRIM(store_name) AS store_name,
        TRIM(city) AS city,
        TRIM(state) AS state,
        TRIM(store_format) AS store_format,
        square_footage,
        opened_date,
        CURRENT_TIMESTAMP AS loaded_at
    FROM source
)

SELECT * FROM cleaned
