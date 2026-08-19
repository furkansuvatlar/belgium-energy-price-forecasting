import pandas as pd

from google.cloud import bigquery

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import xgboost as xgb

import joblib

import numpy as np



# Retrieve data from BigQuery

project_id = "belgium-energy-data-123"

client = bigquery.Client(project=project_id)

query = f"""

SELECT *

FROM `{project_id}.dbt_belgium_energy.fct_energy_prices_features`

ORDER BY price_timestamp ASC

"""

df = client.query(query).to_dataframe()

print(f"Total rows retrieved: {len(df)}")



# Preprocess data

# Deleting first 7 days' lag_168h values to avoid NaN values in the target variable

df = df.dropna().reset_index(drop=True)



# For XGBoost, we convert every numerical columns to float/int

numeric_columns = [

    'price_eur_mwh', 'price_hour', 'day_of_week', 'price_month', 'price_year',

    'price_lag_24h', 'price_lag_168h', 'price_rolling_avg_24h', 'price_rolling_avg_7d'

]



for col in numeric_columns:

    if col in df.columns:

        df[col] = pd.to_numeric(df[col], errors='coerce')





df['is_weekend'] = df['is_weekend'].astype(int)



# is_negative_price is extracted from the target variable, so we can drop it from the features

features = ['price_hour', 'day_of_week', 'price_month', 'price_year', 'price_lag_24h', 'price_lag_168h', 'price_rolling_avg_24h', 'price_rolling_avg_7d', 'is_weekend']

target = 'price_eur_mwh'



X = df[features]

y = df[target]



# Split data into training and testing sets

split_index = int(len(df) * 0.9)



X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]

y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]



print(f"Training set size: {len(X_train)}")

print(f"Testing set size: {len(X_test)}")



# Train XGBoost model

print("Training XGBoost model...")

model = xgb.XGBRegressor(

    n_estimators=500,

    learning_rate=0.05,

    max_depth=6,

    random_state=42,

    objective='reg:squarederror'

)



model.fit(X_train, y_train)

print("Model training completed.")



# Evaluate model

predictions = model.predict(X_test)



mae = mean_absolute_error(y_test, predictions)

rmse = np.sqrt(mean_squared_error(y_test, predictions))

r2 = r2_score(y_test, predictions)



print("\n--- Model Evaluation Metrics ---")

print(f"Mean Absolute Error (MAE): {mae:.2f} €/MWh")

print(f"Root Mean Squared Error (RMSE): {rmse:.2f} €/MWh")

print(f"R-squared (R2): {r2:.2f}")



# Save the model

model_filename = "xgboost_energy_model.pkl"

joblib.dump(model, model_filename)

print(f"Model saved to {model_filename}")