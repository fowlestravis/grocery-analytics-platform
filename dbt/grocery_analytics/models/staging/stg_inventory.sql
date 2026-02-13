WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_inventory') }}
),

cleaned AS (
    SELECT
        -- IDs
        TRIM(product_id) AS product_id,
        TRIM(supplier_id) AS supplier_id,

        -- Product info
        TRIM(product_name) AS product_name,
        TRIM(category) AS category,
        TRIM(supplier_name) AS supplier_name,
        TRIM(warehouse_location) AS warehouse_location,
        TRIM(status) AS status,

        -- Dates
        date_received,
        last_order_date,
        expiration_date,

        -- Quantities
        stock_quantity,
        reorder_level,
        reorder_quantity,

        -- Financials
        unit_price,
        sales_volume,
        inventory_turnover_rate,
        percentage AS turnover_percentage,

        -- Calculated fields
        stock_quantity < reorder_level AS needs_reorder,
        expiration_date - CURRENT_DATE AS days_until_expiration,
        TRIM(status) = 'Active' AS is_active,

        -- Metadata
        CURRENT_TIMESTAMP AS loaded_at

    FROM source
    WHERE product_id IS NOT NULL
)

SELECT * FROM cleaned
