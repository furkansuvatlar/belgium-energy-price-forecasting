WITH staging_data AS (
    SELECT 
        price_timestamp,
        price_eur_mwh,
        forecast_load_mw,
        Solar,
        `Wind Onshore`,
        country AS country_code
    FROM {{ ref('stg_day_ahead_prices') }}
),

feature_engineering AS (
    SELECT 
        price_timestamp,
        CAST(price_timestamp AS DATE) AS price_date,
        EXTRACT(HOUR FROM price_timestamp) AS price_hour,
        EXTRACT(DAYOFWEEK FROM price_timestamp) AS day_of_week,
        EXTRACT(MONTH FROM price_timestamp) AS price_month,
        EXTRACT(YEAR FROM price_timestamp) AS price_year,
        country_code,
        price_eur_mwh,
        forecast_load_mw,
        Solar,
        `Wind Onshore`,
        CASE WHEN price_eur_mwh < 0 THEN TRUE ELSE FALSE END AS is_negative_price,

        -- Lagged features
        LAG(price_eur_mwh, 24) OVER (PARTITION BY country_code ORDER BY price_timestamp) AS price_lag_24h,
        LAG(price_eur_mwh, 168) OVER (PARTITION BY country_code ORDER BY price_timestamp) AS price_lag_168h,

        -- Rolling average features
        AVG(price_eur_mwh) OVER (PARTITION BY country_code ORDER BY price_timestamp ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) AS price_rolling_avg_24h,
        AVG(price_eur_mwh) OVER (PARTITION BY country_code ORDER BY price_timestamp ROWS BETWEEN 167 PRECEDING AND CURRENT ROW) AS price_rolling_avg_7d,

        -- Calendar features
        CASE
            WHEN EXTRACT(DAYOFWEEK FROM price_timestamp) IN (1, 7) THEN 1
            ELSE 0
        END AS is_weekend
    FROM staging_data
)

SELECT *
FROM feature_engineering
WHERE price_lag_24h IS NOT NULL
ORDER BY price_timestamp ASC