import pandas as pd
from entsoe import EntsoePandasClient
from google.cloud import bigquery
import config

def fetch_actual_and_forecast_data():
    # API (Client) initialization
    client = EntsoePandasClient(api_key=config.ENTSOE_API_KEY)

    # Determining the date range for the last 7 days
    now = pd.Timestamp.now(tz='Europe/Brussels')
    end_date = now.normalize() + pd.Timedelta(days=2)
    start_date = end_date - pd.Timedelta(days=7)
    print(f"Connecting to ENTSO-E API to fetch actual data for {config.COUNTRY_CODE} from {start_date} to {end_date}...")
    
    try:
        # 1. Day Ahead Prices (Returns Series)
        ts_prices = client.query_day_ahead_prices(country_code=config.COUNTRY_CODE, start=start_date, end=end_date)
        df_prices = ts_prices.to_frame(name='price_eur_mwh').reset_index().rename(columns={'index': 'price_timestamp'})

        # 2. Day Ahead Load Forecast (Type check added to prevent .to_frame error)
        df_load = client.query_load_forecast(country_code=config.COUNTRY_CODE, start=start_date, end=end_date)
        if isinstance(df_load, pd.Series):
            df_load = df_load.to_frame(name='forecast_load_mw')
        else:
            df_load = df_load.iloc[:, [0]].rename(columns={df_load.columns[0]: 'forecast_load_mw'})
        df_load = df_load.reset_index().rename(columns={'index': 'price_timestamp'})

        # 3. Day Ahead Wind & Solar Forecast (Returns DataFrame)
        df_renewables = client.query_wind_and_solar_forecast(country_code=config.COUNTRY_CODE, start=start_date, end=end_date)
        df_renewables = df_renewables.reset_index().rename(columns={'index': 'price_timestamp'})

        # Merging all dataframes on the timestamp
        df = pd.merge(df_prices, df_load, on='price_timestamp', how='left')
        df = pd.merge(df, df_renewables, on='price_timestamp', how='left')

        # Filling missing values 
        df.fillna(0, inplace=True)
        df['country'] = config.COUNTRY_CODE

        # Load the data into BigQuery
        project_id = getattr(config, 'GCP_PROJECT_ID', "belgium-energy-data-123")
        bq_client = bigquery.Client(project=project_id)
        output_table = f"{project_id}.dbt_belgium_energy.raw_energy_prices"

        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",  
            autodetect=True,  
        )
        job = bq_client.load_table_from_dataframe(df, output_table, job_config=job_config)
        job.result()  

        print(f"Successfully uploaded {len(df)} rows to {output_table}.")
        return df
    except Exception as e:
        print(f"Error fetching or uploading data: {e}")
        return None

if __name__ == "__main__":
    df = fetch_actual_and_forecast_data()
    if df is not None:
        print(df.head())
        print(f"Total rows fetched and uploaded: {len(df)}")