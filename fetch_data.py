import pandas as pd
from entsoe import EntsoePandasClient
from google.cloud import bigquery
import config

def fetch_actual_data():
    # API (Client) initialization
    client = EntsoePandasClient(api_key=config.ENTSOE_API_KEY)

    # Determining the date range for the last 7 days
    end_date = pd.Timestamp.now(tz='Europe/Brussels')
    start_date = end_date - pd.Timedelta(days=7)
    print(f"Connecting to ENTSO-E API to fetch actual data for {config.COUNTRY_CODE} from {start_date} to {end_date}...")
    
    try:
        # Retrieving day-ahead prices from the ENTSO-E API
        ts = client.query_day_ahead_prices(country_code=config.COUNTRY_CODE, start=start_date, end=end_date)
        
        # Converting the retrieved data to a DataFrame
        df = ts.to_frame(name='price_eur_mwh')
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'price_timestamp'}, inplace=True)
        
        # Adding a column for the country code for BigQuery compatibility
        df['country'] = config.COUNTRY_CODE
        print(f"Successfully fetched {len(df)} rows from ENTSO-E API.")

        # BigQuery Initialization
        project_id = getattr(config, 'GCP_PROJECT_ID', 'belgium-energy-data-123')
        bq_client = bigquery.Client(project=project_id)
        output_table = f"{project_id}.dbt_belgium_energy.raw_energy_prices"

        # Configure job to replace/update the raw table with the latest 7-day window
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND"
        )

        print(f"Uploading data to BigQuery table: {output_table}...")
        job = bq_client.load_table_from_dataframe(df, output_table, job_config=job_config)
        job.result()  # Wait for the load job to complete
        
        print("Successfully uploaded latest raw data to BigQuery.")
        return df

    except Exception as e:
        print(f"Error processing data pipeline: {e}")
        return None

if __name__ == "__main__":
    df = fetch_actual_data()
    if df is not None:
        print(df.head())
        print(f"Total number of rows processed: {len(df)}")