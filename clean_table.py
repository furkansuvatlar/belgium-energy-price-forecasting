from google.cloud import bigquery

project_id = "belgium-energy-data-123"
client = bigquery.Client(project=project_id)
table_id = f"{project_id}.dbt_belgium_energy.fact_forecasted_prices"

# Tablonun şemasını koruyarak içeriğini tamamen boşaltır (Truncate)
job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")

# Boş bir DataFrame göndererek tabloyu sıfırlıyoruz
import pandas as pd
empty_df = pd.DataFrame(columns=['forecast_timestamp', 'predicted_price_eur_mwh', 'price_hour', 'day_of_week', 'created_at'])

job = client.load_table_from_dataframe(empty_df, table_id, job_config=job_config)
job.result()

print("fact_forecasted_prices tablosu başarıyla sıfırlandı!")