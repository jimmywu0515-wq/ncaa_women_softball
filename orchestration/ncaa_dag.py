from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'antigravity',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'ncaa_softball_pipeline',
    default_args=default_args,
    description='ETL pipeline for NCAA Softball stats and portal data',
    schedule_interval=timedelta(days=1),
    catchup=False,
) as dag:

    scrape_pbp = BashOperator(
        task_id='scrape_pbp_data',
        bash_command='python3 /app/pipelines/ncaa_pbp_scraper.py',
    )

    scrape_portal = BashOperator(
        task_id='scrape_portal_data',
        bash_command='python3 /app/pipelines/portal_scraper.py',
    )

    # If you were using dbt, the transformation would happen here
    # transform_data = BashOperator(
    #     task_id='dbt_transform',
    #     bash_command='cd /app/dbt && dbt run',
    # )

    [scrape_pbp, scrape_portal]
