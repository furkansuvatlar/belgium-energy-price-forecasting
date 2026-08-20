import pandas as pd
import numpy as np
from google.cloud import bigquery
import joblib

project_id = "belgium-energy-data-123"
client = bigquery.Client(project=project_id)

print("Loading the trained model...")
model = joblib.load("xgboost_energy_model.pkl")

# Retrieve the latest data from BigQuery
query = f"""
SELECT *
FROM `{project_id}.dbt_belgium_energy.fct_energy_prices_features`
ORDER BY price_timestamp DESC
LIMIT 168
"""

df_recent = client.query(query).to_dataframe()
df_recent = df_recent.sort_values('price_timestamp').reset_index(drop=True)

# Preparing the features for prediction
latest_row = df_recent.iloc[-1]
last_timestamp = pd.to_datetime(latest_row['price_timestamp'])

print(f"Last timestamp in the dataset: {last_timestamp}")

# Creating a DataFrame for the next 24 hours
future_dates = [last_timestamp + pd.Timedelta(hours=i) for i in range(1, 25)]
future_df = pd.DataFrame({'forecast_timestamp': future_dates})
future_df['price_hour'] = future_df['forecast_timestamp'].dt.hour
future_df['day_of_week'] = future_df['forecast_timestamp'].dt.dayofweek + 1 ## Monday=1, Sunday=7
future_df['price_month'] = future_df['forecast_timestamp'].dt.month
future_df['price_year'] = future_df['forecast_timestamp'].dt.year
future_df['is_weekend'] = future_df['day_of_week'].apply(lambda x: 1 if x in [1, 7] else 0)

# Last known values for lag features
future_df['price_lag_24h'] = float(latest_row['price_eur_mwh'])  # Last known price for lag_24h
future_df['price_lag_168h'] = float(df_recent.iloc[0]['price_eur_mwh'])  # Price 168 hours ago
future_df['price_rolling_avg_24h'] = float(df_recent['price_eur_mwh'].tail(24).astype(float).mean())
future_df['price_rolling_avg_7d'] = float(df_recent['price_eur_mwh'].astype(float).mean())

features = ['price_hour', 'day_of_week', 'price_month', 'price_year', 'price_lag_24h', 'price_lag_168h', 'price_rolling_avg_24h', 'price_rolling_avg_7d', 'is_weekend']

# Predicting future prices
print("Predicting future prices for the next 24 hours...")
future_df['predicted_price_eur_mwh'] = model.predict(future_df[features])

# Writing the prediction results back to BigQuery
output_table = f"{project_id}.dbt_belgium_energy.fact_forecasted_prices"

# Editing necessary columns for BigQuery
output_df = future_df[['forecast_timestamp', 'predicted_price_eur_mwh', 'price_hour', 'day_of_week']].copy()
output_df['created_at'] = pd.Timestamp.now()

job_config = bigquery.LoadJobConfig(
    write_disposition = "WRITE_APPEND",)

print(f"Writing predictions to BigQuery table: {output_table}...")
job = client.load_table_from_dataframe(output_df, output_table, job_config=job_config)
job.result()

print("Predictions successfully written to BigQuery.")