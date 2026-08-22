import pandas as pd
from google.cloud import bigquery
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib
import numpy as np
import optuna
from tqdm import tqdm
import warnings

# Suppress warnings for cleaner terminal output
warnings.filterwarnings('ignore')

# Retrieve data from BigQuery
project_id = "belgium-energy-data-123"
client = bigquery.Client(project=project_id)
query = f"""
SELECT *
FROM `{project_id}.dbt_belgium_energy.fct_energy_prices_features`
ORDER BY price_timestamp ASC
"""
df = client.query(query).to_dataframe()
print(f"Total rows retrieved from BigQuery: {len(df)}")

# Preprocess data
numeric_columns = [
    'price_eur_mwh', 'price_hour', 'day_of_week', 'price_month', 'price_year',
    'price_lag_24h', 'price_lag_168h', 'price_rolling_avg_24h', 'price_rolling_avg_7d',
    'forecast_load_mw', 'Solar', 'Wind Onshore'
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Cyclical Encoding for hours
df['hour_sin'] = np.sin(2 * np.pi * df['price_hour'] / 24.0)
df['hour_cos'] = np.cos(2 * np.pi * df['price_hour'] / 24.0)

# Correct weekend definition (Saturday=6, Sunday=7)
df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x in [6, 7] else 0)

features = [
    'hour_sin', 'hour_cos', 'day_of_week', 'price_month', 'price_year', 
    'price_lag_24h', 'price_lag_168h', 'price_rolling_avg_24h', 'price_rolling_avg_7d', 
    'is_weekend', 'forecast_load_mw', 'Solar', 'Wind Onshore'
]
target = 'price_eur_mwh'

# Drop missing rows
df = df.dropna(subset=features + [target]).reset_index(drop=True)

X = df[features]
y = df[target]

# Split data into training and testing sets (90% train, 10% test)
split_index = int(len(df) * 0.9)
X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

print(f"Training set size: {len(X_train)} rows")
print(f"Testing set size: {len(X_test)} rows")

# --- OPTUNA HYPERPARAMETER TUNING ---
def objective(trial):
    # Define hyperparameter search space
    param = {
        'n_estimators': trial.suggest_int('n_estimators', 200, 1000),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'max_depth': trial.suggest_int('max_depth', 3, 9),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'random_state': 42,
        'objective': 'reg:squarederror',
        'early_stopping_rounds': 50,
        'eval_metric': 'rmse'
    }

    # Train model with current hyperparameters
    model = xgb.XGBRegressor(**param)
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    # Predict and calculate MAE
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    return mae

# Custom callback to update the tqdm progress bar
class ProgressBarCallback:
    def __init__(self, n_trials):
        self.pbar = tqdm(total=n_trials, desc="Optuna Tuning Progress", unit="trial")
    def __call__(self, study, trial):
        self.pbar.update(1)

# Start Optuna study
N_TRIALS = 30
print("\nStarting Optuna hyperparameter optimization...")
optuna.logging.set_verbosity(optuna.logging.WARNING) # Hide Optuna's default logs for a cleaner progress bar

study = optuna.create_study(direction='minimize') # We want to minimize the MAE
pb_callback = ProgressBarCallback(n_trials=N_TRIALS)
study.optimize(objective, n_trials=N_TRIALS, callbacks=[pb_callback])
pb_callback.pbar.close()

print("\n--- Optuna Best Parameters ---")
for key, value in study.best_params.items():
    print(f"{key}: {value}")

# --- TRAIN FINAL MODEL WITH BEST PARAMS ---
print("\nTraining final XGBoost model with the best parameters...")
best_params = study.best_params
best_params['random_state'] = 42
best_params['objective'] = 'reg:squarederror'
best_params['early_stopping_rounds'] = 50
best_params['eval_metric'] = 'rmse'

final_model = xgb.XGBRegressor(**best_params)
final_model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)
print("Final model training completed.")

# Evaluate final model
predictions = final_model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
rmse = np.sqrt(mean_squared_error(y_test, predictions))
r2 = r2_score(y_test, predictions)

print("\n--- Final Model Evaluation Metrics ---")
print(f"Mean Absolute Error (MAE): {mae:.2f} €/MWh")
print(f"Root Mean Squared Error (RMSE): {rmse:.2f} €/MWh")
print(f"R-squared (R2): {r2:.2f}")

# Save the final model
model_filename = "xgboost_energy_model.pkl"
joblib.dump(final_model, model_filename)
print(f"Model successfully saved to {model_filename}")