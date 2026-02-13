WITH date_spine AS (
    SELECT 
        DATE(transaction_timestamp) AS date_day
    FROM {{ source('raw', 'raw_transactions') }}
    GROUP BY DATE(transaction_timestamp)
),

date_details AS (
    SELECT
        date_day,
        EXTRACT(YEAR FROM date_day) AS year,
        EXTRACT(QUARTER FROM date_day) AS quarter,
        EXTRACT(MONTH FROM date_day) AS month,
        EXTRACT(WEEK FROM date_day) AS week_of_year,
        EXTRACT(DOW FROM date_day) AS day_of_week,
        EXTRACT(DOY FROM date_day) AS day_of_year,
        TO_CHAR(date_day, 'Month') AS month_name,
        TO_CHAR(date_day, 'Day') AS day_name,
        CASE WHEN EXTRACT(DOW FROM date_day) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,
        CASE 
            WHEN EXTRACT(MONTH FROM date_day) = 12 AND EXTRACT(DAY FROM date_day) >= 20 THEN TRUE
            WHEN EXTRACT(MONTH FROM date_day) = 11 AND EXTRACT(DAY FROM date_day) >= 20 THEN TRUE
            ELSE FALSE 
        END AS is_holiday_season
    FROM date_spine
)

SELECT * FROM date_details
