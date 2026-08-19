from google.cloud import bigquery
import pandas as pd
import config
from fetch_data import fetch_actual_data

def upload_to_bigquery(df):
    if df is None or df.empty:
        print("No data to upload to BigQuery.")
        return

    # Initialize BigQuery client
    client = bigquery.Client(project=config.GCP_PROJECT_ID)
    # Target table 
    table_id = f"{config.GCP_PROJECT_ID}.{config.BQ_DATASET_ID}.{config.BQ_TABLE_ID}"
    # Uploading settings
    job_config = bigquery.LoadJobConfig(
        # Overwrite the table if it exists
        write_disposition="WRITE_TRUNCATE",  
        # Automatically detect schema
        autodetect=True,  
    )
    print(f"Uploading data to BigQuery table {table_id}...")

    try:
        # Send the DataFrame to BigQuery
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  

        print(f"Successfully uploaded {len(df)} rows to {table_id}.")
    except Exception as e:
        print(f"Error uploading data to BigQuery: {e}")

if __name__ == "__main__":
    # Fetch the data from the ENTSO-E API
    raw_df = fetch_actual_data()
    # Upload the fetched data to BigQuery
    if raw_df is not None:
        upload_to_bigquery(raw_df)