WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_transactions') }}
),

cleaned AS (
    SELECT
        transaction_id,
        store_id,
        transaction_timestamp,
        sku,
        quantity,
        price,
        ROUND(quantity * price, 2) AS line_total,
        DATE(transaction_timestamp) AS transaction_date,
        EXTRACT(HOUR FROM transaction_timestamp) AS transaction_hour,
        EXTRACT(DOW FROM transaction_timestamp) AS day_of_week,
        CURRENT_TIMESTAMP AS loaded_at
    FROM source
    WHERE quantity > 0
      AND price >= 0
)

SELECT * FROM cleaned
