import pandas as pd
import numpy as np
from google.cloud import bigquery
import joblib

project_id = "belgium-energy-data-123"
client = bigquery.Client(project=project_id)

print("Loading the trained model...")
model = joblib.load("xgboost_energy_model.pkl")

# Retrieve the latest 168 rows from the feature table for lagging
query_recent = f"""
SELECT *
FROM `{project_id}.dbt_belgium_energy.fct_energy_prices_features`
ORDER BY price_timestamp DESC
LIMIT 168
"""
df_recent = client.query(query_recent).to_dataframe()
df_recent = df_recent.sort_values('price_timestamp').reset_index(drop=True)

latest_row = df_recent.iloc[-1]
last_timestamp = pd.to_datetime(latest_row['price_timestamp'])
print(f"Last timestamp in the dataset: {last_timestamp}")

# Create DataFrame for the next 24 hours
future_dates = [last_timestamp + pd.Timedelta(hours=i) for i in range(1, 25)]
future_df = pd.DataFrame({'forecast_timestamp': future_dates})

# 1. Retrieve the future weather and load forecast from raw_energy_prices
start_future_str = future_dates[0].strftime('%Y-%m-%d %H:%M:%S')
end_future_str = future_dates[-1].strftime('%Y-%m-%d %H:%M:%S')

query_future_weather = f"""
SELECT price_timestamp as forecast_timestamp, forecast_load_mw, Solar, `Wind Onshore`
FROM `{project_id}.dbt_belgium_energy.raw_energy_prices`
WHERE price_timestamp BETWEEN '{start_future_str}' AND '{end_future_str}'
ORDER BY price_timestamp ASC
"""
df_weather = client.query(query_future_weather).to_dataframe()

# Ensure matching timestamp formats before merging
future_df['forecast_timestamp'] = pd.to_datetime(future_df['forecast_timestamp']).dt.tz_localize(None)
if not df_weather.empty:
    df_weather['forecast_timestamp'] = pd.to_datetime(df_weather['forecast_timestamp']).dt.tz_localize(None)

# Merge future dates with the weather/load forecasts
future_df = pd.merge(future_df, df_weather, on='forecast_timestamp', how='left')

# Fill missing weather data forward just in case ENTSO-E had a gap
future_df = future_df.ffill().fillna(0)

# 2. Add standard and cyclical time features
future_df['price_hour'] = future_df['forecast_timestamp'].dt.hour
future_df['hour_sin'] = np.sin(2 * np.pi * future_df['price_hour'] / 24.0)
future_df['hour_cos'] = np.cos(2 * np.pi * future_df['price_hour'] / 24.0)

future_df['day_of_week'] = future_df['forecast_timestamp'].dt.dayofweek + 1
future_df['price_month'] = future_df['forecast_timestamp'].dt.month
future_df['price_year'] = future_df['forecast_timestamp'].dt.year
future_df['is_weekend'] = future_df['day_of_week'].apply(lambda x: 1 if x in [6, 7] else 0)

# 3. Dynamic Lag Features
future_df['price_lag_24h'] = df_recent['price_eur_mwh'].iloc[-24:].values
future_df['price_lag_168h'] = df_recent['price_eur_mwh'].iloc[0:24].values
future_df['price_rolling_avg_24h'] = df_recent['price_eur_mwh'].iloc[-24:].mean()
future_df['price_rolling_avg_7d'] = df_recent['price_eur_mwh'].mean()

features = [
    'hour_sin', 'hour_cos', 'day_of_week', 'price_month', 'price_year', 
    'price_lag_24h', 'price_lag_168h', 'price_rolling_avg_24h', 'price_rolling_avg_7d', 
    'is_weekend', 'forecast_load_mw', 'Solar', 'Wind Onshore'
]

# Predicting future prices
print("Predicting future prices for the next 24 hours...")
future_df['predicted_price_eur_mwh'] = model.predict(future_df[features])

# Output processing
output_table = f"{project_id}.dbt_belgium_energy.fact_forecasted_prices"
output_df = future_df[['forecast_timestamp', 'predicted_price_eur_mwh', 'price_hour', 'day_of_week']].copy()
output_df['created_at'] = pd.Timestamp.now()

# Fix BigQuery Timestamp formatting issues
output_df['forecast_timestamp'] = pd.to_datetime(output_df['forecast_timestamp'])
output_df['created_at'] = pd.to_datetime(output_df['created_at'])

job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_APPEND"
)
print(f"Writing predictions to BigQuery table: {output_table}...")
job = client.load_table_from_dataframe(output_df, output_table, job_config=job_config)
job.result()

print("Predictions successfully written to BigQuery.")