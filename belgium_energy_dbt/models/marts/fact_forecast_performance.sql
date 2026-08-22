{{ config(materialized='table') }}

with actuals as (
    select
        cast(price_timestamp as timestamp) as timestamp,
        price_eur_mwh as actual_price
    from {{ ref('stg_day_ahead_prices') }}
),

forecasts as (
    select
        timestamp,
        predicted_price
    from (
        select
            cast(forecast_timestamp as timestamp) as timestamp,
            predicted_price_eur_mwh as predicted_price,
            row_number() over (partition by forecast_timestamp order by created_at desc) as rn
        from {{ target.project }}.dbt_belgium_energy.fact_forecasted_prices
    )
    where rn = 1
)

select
    coalesce(a.timestamp, f.timestamp) as datetime,
    a.actual_price,
    f.predicted_price,
    abs(a.actual_price - f.predicted_price) as absolute_error
from actuals a
full outer join forecasts f
    on a.timestamp = f.timestamp
order by datetime desc