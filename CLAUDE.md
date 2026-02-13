# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grocery analytics platform using a modern data stack: Airflow (orchestration) + dbt (transformation) + PostgreSQL 15 (warehouse). The project includes synthetic grocery data with known price elasticities for demand analysis validation.

## Infrastructure Commands

```bash
# Start Postgres warehouse
docker-compose up -d

# Start Airflow stack (webserver + scheduler + metadata postgres)
docker-compose -f docker-compose-airflow.yml up -d

# Airflow UI: http://localhost:8080 (airflow/airflow)
# Data Postgres: localhost:5432 (analytics_user/analytics_pass/grocery_analytics)
# Airflow Postgres: localhost:5433

# Interactive Postgres shell
docker exec -it grocery_postgres psql -U analytics_user -d grocery_analytics
```

## dbt Commands

All dbt commands run from `dbt/grocery_analytics/`:

```bash
dbt run                            # Run all models
dbt run --select staging           # Run one layer
dbt run --select tag:synthetic     # Run by tag
dbt test                           # Run data quality tests
dbt debug                          # Test database connection
```

## Data Loading Scripts

```bash
python3 scripts/generate_data.py           # Generate synthetic CSVs to data/raw/
python3 scripts/load_data_to_postgres.py   # Load raw CSVs to Postgres
python3 scripts/load_synthetic_data.py     # Load synthetic grocery data
python3 scripts/fetch_kaggle_inventory.py  # Download Kaggle dataset
python3 scripts/load_kaggle_to_postgres.py # Load Kaggle data
./setup_synthetic_data.sh                  # End-to-end synthetic data setup
```

## Architecture

### Data Flow

Raw CSVs → Python load scripts → Postgres `raw` schema → dbt staging (views) → dbt dimensions/marts (tables) → analysis/ scripts → validation_results/

### dbt Model Layers

| Layer | Schema | Materialization | Prefix | Example |
|-------|--------|-----------------|--------|---------|
| Staging | `staging` | view | `stg_` | `stg_transactions` |
| Dimensions | `analytics` | table | `dim_` | `dim_product` |
| Facts/Marts | `analytics` | table | `fct_`/`mart_` | `fct_synthetic_daily_sales` |

Two parallel model tracks exist: one for the generated/Kaggle data (`stg_transactions`, `dim_product`, `fact_sales`) and one for synthetic grocery data with elasticities (`stg_synthetic_transactions`, `dim_synthetic_products`, `fct_synthetic_daily_sales`, `mart_elasticity_validation`).

### Airflow Pipeline

Single DAG `grocery_analytics_pipeline` runs daily at 2 AM UTC. Task chain:
`fetch_kaggle_inventory → load_kaggle_to_postgres → generate_transaction_data → load_data_to_postgres → dbt_run_staging → dbt_run_dimensions → dbt_run_marts → dbt_test`

All Airflow tasks use `BashOperator`. Inside the container, the project root is `/opt/airflow`.

## Demand Analysis

```bash
python3 analysis/demand_analysis.py    # Elasticity validation (outputs to validation_results/)
```

## Conventions

- **File naming**: kebab-case for docs/markdown, snake_case for Python
- **SQL models**: `stg_[entity]`, `dim_[entity]`, `fct_[entity]`, `mart_[analysis]`
- **Database schemas**: `raw` (ingested), `staging` (cleaned views), `analytics` (production tables)
- **SQLAlchemy**: Use `text()` wrapper for raw SQL (SQLAlchemy 2.0 compatibility)
- **Environment variables**: Loaded via `python-dotenv` from `config/.env`

## Key Dependencies

`dbt-postgres==1.7.4`, `faker==20.1.0`, `pandas==2.1.4`, `psycopg2-binary==2.9.9`, `python-dotenv==1.0.0`
