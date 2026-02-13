# Grocery Analytics Platform

A modern data stack for grocery demand analysis, featuring automated ETL pipelines, dimensional modeling, and **validated price elasticity estimation**. Built with Airflow, dbt, and PostgreSQL.

**Key Achievement:** Successfully recovered known price elasticities from synthetic data with **2.4-2.5% average error**, validating the methodology for application to real vendor data.

## Validation Results

The platform includes a complete elasticity validation pipeline that proves the methodology works before applying it to real data. Using synthetic grocery transactions with known ground-truth elasticities, the log-log regression approach recovers true values with high accuracy.

| Category   | Products | Avg True Elasticity | Avg Estimated | Avg Error | Error Range |
|------------|----------|---------------------|---------------|-----------|-------------|
| Fruit      | 20       | -1.435              | -1.441        | 2.4%      | 0.3% - 9.1% |
| Vegetables | 13       | -1.038              | -1.042        | 2.5%      | 0.5% - 4.4% |

### Product-Level Validation

![Product-level elasticity validation showing tight clustering along the perfect estimation diagonal](validation_results/product_validation.png)

Product-level estimates show strong correlation with ground truth values across both categories. Points cluster tightly along the diagonal, confirming unbiased estimation across the full elasticity range (-0.4 to -2.5).

### Error Distribution

![Distribution of estimation errors centered near zero](validation_results/error_distribution.png)

Errors are centered near zero with most products under 4% error, indicating the methodology produces reliable, unbiased estimates.

### Methodology

**Estimation approach:** Log-log regression per product

```
ln(Q) = β₀ + β₁ × ln(P) + ε
```

where β₁ is the price elasticity estimate. Product-level time series estimation avoids the Simpson's paradox effect that confounds category-level aggregation.

**Data:** 434,016 synthetic transactions across 33 products, 12 stores, and 3 years (2022-2024).

## Architecture

### Data Flow

```
Raw CSVs → Python load scripts → Postgres (raw schema)
                                       ↓
                              dbt staging (views)
                                       ↓
                           dbt dimensions/marts (tables)
                                       ↓
                  analysis/demand_analysis.py → validation_results/
```

### dbt Model Layers

| Layer | Schema | Materialization | Prefix | Example |
|-------|--------|-----------------|--------|---------|
| Staging | `staging` | view | `stg_` | `stg_transactions` |
| Dimensions | `analytics` | table | `dim_` | `dim_product` |
| Facts/Marts | `analytics` | table | `fct_`/`mart_` | `fct_synthetic_daily_sales` |

Two parallel model tracks:
- **Generated/Kaggle data:** `stg_transactions` → `dim_product` → `fact_sales` → `mart_daily_store_performance`
- **Synthetic grocery data:** `stg_synthetic_transactions` → `dim_synthetic_products` → `fct_synthetic_daily_sales` → `mart_elasticity_validation`

### Airflow Pipeline

Single DAG `grocery_analytics_pipeline` runs daily at 2 AM UTC:

```
fetch_kaggle_inventory → load_kaggle_to_postgres → generate_transaction_data → load_data_to_postgres
    → dbt_run_staging → dbt_run_dimensions → dbt_run_marts → dbt_test
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ with virtualenv
- PostgreSQL client (optional, for direct queries)

### Infrastructure

```bash
# Start Postgres warehouse
docker-compose up -d

# Start Airflow stack (webserver + scheduler + metadata postgres)
docker-compose -f docker-compose-airflow.yml up -d

# Airflow UI: http://localhost:8080 (airflow/airflow)
# Data Postgres: localhost:5432 (analytics_user/analytics_pass/grocery_analytics)
```

### Data Loading

```bash
# End-to-end synthetic data setup
./setup_synthetic_data.sh

# Or run individual steps:
python3 scripts/generate_data.py           # Generate synthetic CSVs
python3 scripts/load_data_to_postgres.py   # Load raw CSVs to Postgres
python3 scripts/load_synthetic_data.py     # Load synthetic grocery data
python3 scripts/fetch_kaggle_inventory.py  # Download Kaggle dataset
python3 scripts/load_kaggle_to_postgres.py # Load Kaggle data
```

### dbt

All dbt commands run from `dbt/grocery_analytics/`:

```bash
dbt run                            # Run all models
dbt run --select staging           # Run one layer
dbt run --select tag:synthetic     # Run by tag
dbt test                           # Run data quality tests
```

### Demand Analysis

```bash
# Run elasticity validation against synthetic data
python3 analysis/demand_analysis.py

# Results output to validation_results/
```

## Project Structure

```
grocery-analytics-platform/
├── airflow/
│   ├── dags/
│   │   └── grocery_pipeline.py        # Main DAG definition
│   ├── config/
│   ├── logs/
│   ├── models/
│   └── plugins/
├── config/
│   └── .env                           # Database connection settings
├── data/
│   ├── kaggle/                        # Kaggle inventory dataset
│   ├── raw/                           # Generated transaction data
│   └── synthetic_grocery/             # Synthetic data with known elasticities
├── dbt/grocery_analytics/
│   └── models/
│       ├── staging/                   # stg_ views (cleaning layer)
│       ├── dimensions/                # dim_ and fact_ tables
│       └── marts/                     # mart_ analysis tables
├── analysis/
│   └── demand_analysis.py             # Elasticity estimation & validation
├── docs/
│   └── archive/
├── scripts/
│   ├── fetch_kaggle_inventory.py
│   ├── generate_data.py
│   ├── load_data_to_postgres.py
│   ├── load_kaggle_to_postgres.py
│   └── load_synthetic_data.py
├── validation_results/                # Elasticity validation output
│   ├── VALIDATION_REPORT.md
│   ├── category_validation.png
│   ├── product_validation.png
│   ├── error_distribution.png
│   ├── category_results.csv
│   └── product_results.csv
├── docker-compose.yml                 # Postgres warehouse
├── docker-compose-airflow.yml         # Airflow stack
├── setup_synthetic_data.sh            # End-to-end data setup
└── requirements.txt
```

## Key Dependencies

`dbt-postgres`, `pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`, `sqlalchemy`, `psycopg2-binary`, `faker`, `python-dotenv`
