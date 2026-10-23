from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator


def on_failure_callback(context):
    """Called when any task fails. Logs failure details for later Slack integration."""
    task_id = context['task_instance'].task_id
    error = context['exception']
    exec_date = context['dag_run'].execution_date

    with open('/opt/airflow/logs/failure_alerts.log', 'a') as f:
        f.write(f"{datetime.now()} | FAILED: {task_id} | {error}\n")


default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': on_failure_callback,
}

dag = DAG(
    'daily_grocery_refresh',
    default_args=default_args,
    description='Daily synthetic grocery data refresh: generate, load, transform, analyze',
    schedule_interval='0 6 * * *',
    catchup=False,
    tags=['grocery', 'synthetic', 'daily'],
)

generate_data = BashOperator(
    task_id='generate_synthetic_data',
    bash_command='cd /opt/airflow && python scripts/generate_data.py',
    dag=dag,
)

load_data = BashOperator(
    task_id='load_data_to_postgres',
    bash_command='cd /opt/airflow && python scripts/load_synthetic_data.py',
    dag=dag,
)

dbt_run = BashOperator(
    task_id='dbt_run_synthetic',
    bash_command='cd /opt/airflow/dbt/grocery_analytics && dbt run --select tag:synthetic tag:elasticity',
    dag=dag,
)

dbt_test = BashOperator(
    task_id='dbt_test_synthetic',
    bash_command='cd /opt/airflow/dbt/grocery_analytics && dbt test --select tag:synthetic tag:elasticity source:synthetic_grocery.elasticity_estimates',
    dag=dag,
)

run_analysis = BashOperator(
    task_id='run_demand_analysis',
    bash_command='cd /opt/airflow && python analysis/demand_analysis.py',
    dag=dag,
)

generate_data >> load_data >> dbt_run >> run_analysis >> dbt_test
