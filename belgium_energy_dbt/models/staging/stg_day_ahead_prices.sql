WITH raw_data AS (
    SELECT
        TIMESTAMP_TRUNC(CAST(price_timestamp AS TIMESTAMP), HOUR) AS price_timestamp,
        CAST(price_eur_mwh AS FLOAT64) AS price_eur_mwh,
        country
    FROM `belgium-energy-data-123.dbt_belgium_energy.raw_energy_prices`
)

SELECT
    price_timestamp,
    AVG(CAST(price_eur_mwh AS FLOAT64)) AS price_eur_mwh,
    ANY_VALUE(country) AS country
FROM raw_data
GROUP BY 1