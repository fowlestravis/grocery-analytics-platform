from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Default arguments for the DAG
default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'grocery_analytics_pipeline',
    default_args=default_args,
    description='Daily grocery analytics pipeline',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    catchup=False,
    tags=['grocery', 'analytics'],
)

# Task 1: Generate new transaction data
generate_data = BashOperator(
    task_id='generate_transaction_data',
    bash_command='cd /opt/airflow && python scripts/generate_data.py',
    dag=dag,
)

# Task 2: Load data to Postgres
load_data = BashOperator(
    task_id='load_data_to_postgres',
    bash_command='cd /opt/airflow && python scripts/load_data_to_postgres.py',
    dag=dag,
)

# Task 3: Fetch Kaggle inventory data
fetch_kaggle = BashOperator(
    task_id='fetch_kaggle_inventory',
    bash_command='cd /opt/airflow && python scripts/fetch_kaggle_inventory.py',
    dag=dag,
)

# Task 4: Load Kaggle data to Postgres
load_kaggle = BashOperator(
    task_id='load_kaggle_to_postgres',
    bash_command='cd /opt/airflow && python scripts/load_kaggle_to_postgres.py',
    dag=dag,
)

# Task 3: Run dbt staging models
dbt_staging = BashOperator(
    task_id='dbt_run_staging',
    bash_command='cd /opt/airflow/dbt/grocery_analytics && dbt run --select staging',
    dag=dag,
)

# Task 4: Run dbt dimensional models
dbt_dimensions = BashOperator(
    task_id='dbt_run_dimensions',
    bash_command='cd /opt/airflow/dbt/grocery_analytics && dbt run --select dimensions',
    dag=dag,
)

# Task 5: Run dbt marts
dbt_marts = BashOperator(
    task_id='dbt_run_marts',
    bash_command='cd /opt/airflow/dbt/grocery_analytics && dbt run  --select marts',
    dag=dag,
)
# Task 6: Run dbt tests
dbt_test = BashOperator(
    task_id='dbt_test',
    bash_command='cd /opt/airflow/dbt/grocery_analytics && dbt test',
    dag=dag,
)

# Define task dependencies (the workflow)
fetch_kaggle >> load_kaggle >> generate_data >> load_data >> dbt_staging >> dbt_dimensions >> dbt_marts >> dbt_test
