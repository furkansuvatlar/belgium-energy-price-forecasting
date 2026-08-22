WITH raw_data AS (
    SELECT
        TIMESTAMP_TRUNC(CAST(price_timestamp AS TIMESTAMP), HOUR) AS price_timestamp,
        CAST(price_eur_mwh AS FLOAT64) AS price_eur_mwh,
        CAST(forecast_load_mw AS FLOAT64) AS forecast_load_mw,
        CAST(Solar AS FLOAT64) AS Solar,
        CAST(`Wind Onshore` AS FLOAT64) AS `Wind Onshore`,
        country
    FROM `belgium-energy-data-123.dbt_belgium_energy.raw_energy_prices`
)

SELECT
    price_timestamp,
    AVG(price_eur_mwh) AS price_eur_mwh,
    AVG(forecast_load_mw) AS forecast_load_mw,
    AVG(Solar) AS Solar,
    AVG(`Wind Onshore`) AS `Wind Onshore`,
    ANY_VALUE(country) AS country
FROM raw_data
GROUP BY 1