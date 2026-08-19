import pandas as pd
import time
from datetime import datetime
from entsoe import EntsoePandasClient
import config
from google.cloud import bigquery

def backfill_historical_data(years=3):
    client_entsoe = EntsoePandasClient(api_key=config.ENTSOE_API_KEY)
    client_bq = bigquery.Client(project=config.GCP_PROJECT_ID)
    table_id = f"{config.GCP_PROJECT_ID}.{config.BQ_DATASET_ID}.{config.BQ_TABLE_ID}"

    # End date is now, start date is 'years' years ago
    end_date = pd.Timestamp.now(tz='Europe/Brussels')
    start_date = end_date - pd.DateOffset(years=years)
    print(f"Backfilling data from {start_date} to {end_date} for {config.COUNTRY_CODE}...")

    # Fetching data in chunks of 1 month to avoid API limits
    date_range = pd.date_range(start=start_date, end=end_date, freq='MS')  # Monthly start frequency
    all_dfs = []

    for i in range(len(date_range) - 1):
        chunk_start = date_range[i]
        chunk_end = date_range[i + 1] - pd.Timedelta(seconds=1)  # End of the month
        print(f"Fetching data from {chunk_start} to {chunk_end}...")
        try:
            ts = client_entsoe.query_day_ahead_prices(country_code=config.COUNTRY_CODE, start=chunk_start, end=chunk_end)
            df = ts.to_frame(name='price_eur_mwh')
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'timestamp'}, inplace=True)
            df['country'] = config.COUNTRY_CODE
            all_dfs.append(df)
            time.sleep(1)  
        except Exception as e:
            print(f"Error fetching data for {chunk_start} to {chunk_end}: {e}")
    if not all_dfs:
        print("No data fetched. Exiting backfill process.")
        return

    # Concatenate all dataframes
    full_df = pd.concat(all_dfs, ignore_index=True)
    # Duplicate removal based on timestamp and country
    full_df.drop_duplicates(subset=['timestamp', 'country'], inplace=True)
    print(f"Total rows fetched: {len(full_df)}. Uploading to BigQuery...")

    # Uploading to BigQuery
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  
        autodetect=True,  
    )

    try:
        job = client_bq.load_table_from_dataframe(full_df, table_id, job_config=job_config)
        job.result()  
        print(f"Successfully uploaded {len(full_df)} rows to {table_id}.")
    except Exception as e:
        print(f"Error uploading data to BigQuery: {e}")

if __name__ == "__main__":
    backfill_historical_data(years=3) 