from datetime import datetime, timedelta
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

DBT = "/home/tingn/dbt-venv/bin/dbt"
PY = "/home/tingn/pipeline-venv/bin/python"
REPO = "/mnt/c/Users/tingn/TradeSafe"
ENV = "set -a; source /home/tingn/.pipeline.env; set +a"
DAY = "$(date -d yesterday +%F)"
MODELS = "stg_initial stg_prices company_latest_price"

with DAG(
    dag_id="tradesafe_daily",
    start_date=datetime(2026, 10, 1),
    schedule="0 11 * * 2-6",
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
) as dag:
    ingest = BashOperator(
        task_id="ingest",
        bash_command=f"{ENV}; {PY} {REPO}/Ingestion/dailyIngest.py {DAY}",
    )
    load = BashOperator(
        task_id="load",
        bash_command=f"{PY} {REPO}/Ingestion/loadDay.py {DAY}",
    )
    transform = BashOperator(
        task_id="transform",
        bash_command=f"{DBT} run --project-dir {REPO}/dbt --select {MODELS}",
    )
    test = BashOperator(
        task_id="test",
        bash_command=f"{DBT} test --project-dir {REPO}/dbt --select {MODELS}",
    )

    ingest >> load >> transform >> test
