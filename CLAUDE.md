# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grocery analytics platform using a modern data stack: Airflow (orchestration) + dbt (transformation) + PostgreSQL 15 (warehouse). Includes synthetic grocery data with known price elasticities to validate a log-log regression demand analysis methodology (~2.5% average error).

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

# Python environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Analysis scripts also need: scipy numpy matplotlib seaborn sqlalchemy
```

## dbt Commands

All dbt commands run from `dbt/grocery_analytics/`:

```bash
dbt run                            # Run all models
dbt run --select staging           # Run one layer
dbt run --select tag:synthetic     # Run by tag
dbt run --select model_name        # Run a single model
dbt test                           # Run data quality tests
dbt debug                          # Test database connection
```

dbt profile (`grocery_analytics`) must be configured in `~/.dbt/profiles.yml` for local dev. A container-specific profile exists at `dbt/profiles/profiles.yml` (uses `env_var('GROCERY_DB_HOST')` for the host).

## Data Loading Scripts

```bash
./setup_synthetic_data.sh                  # End-to-end synthetic data setup
python3 scripts/generate_data.py           # Generate synthetic CSVs to data/raw/
python3 scripts/load_data_to_postgres.py   # Load raw CSVs to Postgres
python3 scripts/load_synthetic_data.py     # Load synthetic grocery data to raw schema
python3 scripts/fetch_kaggle_inventory.py  # Download Kaggle dataset
python3 scripts/load_kaggle_to_postgres.py # Load Kaggle data
```

## Demand Analysis

```bash
python3 analysis/demand_analysis.py    # Elasticity validation (outputs to validation_results/)
```

Uses log-log regression (`ln(Q) = β₀ + β₁×ln(P) + ε`) per product. Reads from `analytics_analytics.mart_elasticity_validation` and `analytics_analytics.fct_synthetic_daily_sales`.

## Architecture

### Data Flow

Raw CSVs → Python load scripts → Postgres `raw` schema → dbt staging (views) → dbt dimensions/marts (tables) → `analysis/demand_analysis.py` → `validation_results/`

### dbt Model Layers

| Layer | Schema | Materialization | Prefix | Example |
|-------|--------|-----------------|--------|---------|
| Staging | `staging` | view | `stg_` | `stg_transactions` |
| Dimensions | `analytics` | table | `dim_` | `dim_product` |
| Facts/Marts | `analytics` | table | `fct_`/`mart_` | `fct_synthetic_daily_sales` |

**Two parallel model tracks:**
- **Generated/Kaggle:** `stg_transactions` → `dim_product` → `fact_sales` → `mart_daily_store_performance` (sources from `public` schema)
- **Synthetic grocery:** `stg_synthetic_transactions` → `dim_synthetic_products` → `fct_synthetic_daily_sales` → `mart_elasticity_validation` (sources from `raw` schema, defined in `sources_synthetic.yml`)

### Schema Naming Quirk

dbt prepends the target schema to custom schemas. With target schema `analytics` and custom schema `analytics`, the actual Postgres schema becomes `analytics_analytics`. Queries in Python scripts must use this combined name (e.g., `analytics_analytics.mart_elasticity_validation`).

### Airflow Pipelines

**Active DAG — `daily_grocery_refresh`** (6 AM UTC daily):
`generate_synthetic_data → load_data_to_postgres → dbt_run_synthetic → run_demand_analysis`

Runs the full synthetic elasticity validation pipeline. Failure callback logs to `/opt/airflow/logs/failure_alerts.log`.

**Legacy DAG — `grocery_analytics_pipeline`** (2 AM UTC daily):
`fetch_kaggle_inventory → load_kaggle_to_postgres → generate_transaction_data → load_data_to_postgres → dbt_run_staging → dbt_run_dimensions → dbt_run_marts → dbt_test`

All Airflow tasks use `BashOperator`. Inside the container, the project root is `/opt/airflow`. The Airflow compose file mounts `scripts/`, `dbt/`, `data/`, `config/`, `analysis/`, and `validation_results/` into the container.

### Container Networking

Airflow containers reach the data warehouse Postgres via `host.docker.internal` (Docker Desktop feature). The `GROCERY_DB_HOST` env var is set in `docker-compose-airflow.yml` and read by all Python scripts with a `localhost` fallback. The two compose files (`docker-compose.yml` for the warehouse, `docker-compose-airflow.yml` for Airflow) run on separate Docker networks.

## Conventions

- **File naming**: kebab-case for docs/markdown, snake_case for Python and SQL
- **SQL models**: `stg_[entity]`, `dim_[entity]`, `fct_[entity]`, `mart_[analysis]`
- **Database schemas**: `raw` (ingested), `staging` (cleaned views), `analytics` (production tables)
- **SQLAlchemy**: Use `text()` wrapper for raw SQL (SQLAlchemy 2.0 compatibility)
- **DB host**: Scripts use `os.environ.get("GROCERY_DB_HOST", "localhost")` — containers set this to `host.docker.internal`, local dev falls back to `localhost`
- **DB credentials**: Hardcoded in Python scripts (not loaded from env vars despite `config/.env` being in `.gitignore`)
- **SQLAlchemy transactions**: Use `engine.begin()` context manager (compatible with both SQLAlchemy 1.4 in Airflow and 2.0 locally)

## Key Dependencies

`dbt-postgres==1.7.4`, `faker==20.1.0`, `pandas==2.1.4`, `psycopg2-binary==2.9.9`, `python-dotenv==1.0.0`

Analysis additionally requires: `scipy`, `numpy`, `matplotlib`, `seaborn`, `sqlalchemy`
