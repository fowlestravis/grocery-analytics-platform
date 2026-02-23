# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grocery analytics platform using a modern data stack: Airflow (orchestration) + dbt (transformation) + PostgreSQL 15 (warehouse). Includes synthetic grocery data with known price elasticities to validate a log-log regression demand analysis methodology (~2.5% average error).

## Infrastructure Commands

```bash
# Start Postgres warehouse + Metabase
docker-compose up -d

# Start Airflow stack (webserver + scheduler + metadata postgres)
docker-compose -f docker-compose-airflow.yml up -d

# Metabase UI: http://localhost:3000
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

## Metabase (BI Dashboard)

```bash
# Metabase runs as part of the warehouse compose stack
docker-compose up -d                   # Starts both Postgres and Metabase

# Metabase UI: http://localhost:3000
# Public dashboard (no login): http://localhost:3000/public/dashboard/<uuid>#refresh=900
# Setup script (creates dashboard + cards via API):
python3 scripts/setup_metabase_dashboard.py
```

Metabase connects to `grocery_postgres` via Docker's internal network (host: `postgres`, port: `5432`). Its internal metadata (dashboards, saved questions, user accounts) is stored in an H2 database on the `metabase_data` Docker volume.

### Dashboard: Grocery Analytics Overview

7 cards using native SQL queries against `analytics_analytics` schema:

| Card | Type | Source Table(s) |
|------|------|-----------------|
| Total Products | KPI (scalar) | `dim_synthetic_products` |
| Total Transactions | KPI (scalar) | `fct_synthetic_daily_sales` |
| Data Freshness | KPI (scalar) | `fct_synthetic_daily_sales` |
| Sales by Category | Bar chart | `fct_synthetic_daily_sales` |
| True vs Estimated Elasticity | Scatter plot | `fct_synthetic_daily_sales` + `dim_synthetic_products` |
| Daily Sales Trend | Line chart | `fct_synthetic_daily_sales` |
| Avg Validation Error % | Big number | `fct_synthetic_daily_sales` + `dim_synthetic_products` |

The elasticity scatter plot and validation error card compute estimated elasticity in SQL using `regr_slope(ln(units_sold), ln(price))` — Postgres's built-in linear regression aggregate.

Auto-refresh: append `#refresh=900` to the public dashboard URL for 15-minute refresh (client-side). Public sharing is enabled; the public link is read-only and requires no authentication.

## Demand Analysis

```bash
python3 analysis/demand_analysis.py    # Elasticity validation (outputs to validation_results/)
```

### Economics Methodology

**Model:** Log-log (constant elasticity) demand model

```
ln(Q) = β₀ + β₁×ln(P) + ε
```

Where Q = quantity demanded, P = price, and β₁ = price elasticity of demand. The log-log form assumes constant elasticity across the price range — a 1% price increase always causes a β₁% change in quantity.

**Two estimation methods:**

| Method | Approach | Granularity | Result |
|--------|----------|-------------|--------|
| Method 1 (Aggregate) | `scipy.stats.linregress` on category-level avg price/qty | One estimate per category | Does not work — cross-product variation confounds the estimate |
| Method 2 (Product Time Series) | `scipy.stats.linregress` on daily ln(price) vs ln(qty) per product | One estimate per product | Works — ~2.4% avg error across 32 products |

**Why Method 2 works and Method 1 doesn't:** Method 1 regresses across products within a category, conflating different products' base demand levels with price effects. Method 2 isolates within-product price variation over time, which is the proper identification strategy for demand elasticity.

**Data quality filters in Method 2:**
- Price coefficient of variation > 5% (sufficient price variation)
- Minimum 50 observations per product
- Filters out `ln(0)` (zero units or zero price)

### Validation Data

- 32 products across 4 categories (Dairy, Produce, Snacks, Beverages)
- 12 stores, 730 days (2 years), 280,320 transaction records
- True elasticities embedded in data generation (`scripts/generate_data.py`)
- Synthetic data uses demand function: `Q = base_qty × (P/base_P)^elasticity × noise`

### SQL-Based Estimation (Metabase)

The Metabase dashboard computes elasticity directly in Postgres using the `regr_slope` aggregate, which is equivalent to Method 2:

```sql
SELECT p.product_name, p.true_elasticity,
       regr_slope(ln(s.units_sold::float), ln(s.price::float)) AS estimated_elasticity
FROM analytics_analytics.fct_synthetic_daily_sales s
JOIN analytics_analytics.dim_synthetic_products p ON s.upc = p.upc
WHERE s.price > 0 AND s.units_sold > 0
GROUP BY p.upc, p.product_name, p.true_elasticity
```

### Output Files

All outputs go to `validation_results/`:
- `VALIDATION_REPORT.md` — full markdown report
- `category_validation.png`, `product_validation.png` — scatter plots
- `error_distribution.png` — error histogram
- `category_results.csv`, `product_results.csv` — raw results

## Architecture

### Data Flow

```
Raw CSVs → Python load scripts → Postgres `raw` schema → dbt staging (views)
→ dbt dimensions/marts (tables) → analysis/demand_analysis.py → validation_results/
                                 → Metabase dashboard (live SQL queries)
```

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

- **Metabase → Postgres:** Same compose file (`docker-compose.yml`), shared Docker network. Metabase connects using service name `postgres` as the host.
- **Airflow → Postgres:** Separate compose file (`docker-compose-airflow.yml`), different Docker network. Uses `host.docker.internal` (Docker Desktop feature) via `GROCERY_DB_HOST` env var. Python scripts fall back to `localhost` for local dev.

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

Metabase dashboard setup requires: `requests`

## Services Summary

| Service | Container | Port | Compose File | Restart |
|---------|-----------|------|--------------|---------|
| PostgreSQL 15 (warehouse) | `grocery_postgres` | 5432 | `docker-compose.yml` | unless-stopped |
| Metabase (BI dashboard) | `grocery_metabase` | 3000 | `docker-compose.yml` | unless-stopped |
| Airflow Webserver | `airflow_webserver` | 8080 | `docker-compose-airflow.yml` | always |
| Airflow Scheduler | `airflow_scheduler` | — | `docker-compose-airflow.yml` | always |
| PostgreSQL 15 (Airflow metadata) | `airflow_postgres` | 5433 | `docker-compose-airflow.yml` | always |
