import os

ENTSOE_API_KEY = os.getenv("ENTSOE_API_KEY", "5f365dae-1041-4ada-be69-e4cfe563827c")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "belgium-energy-data-123")
BQ_DATASET_ID = "dbt_belgium_energy"
BQ_TABLE_ID = "raw_belgium_day_ahead_prices"
COUNTRY_CODE = "BE"