# Grocery Analytics Platform

A modern data stack for grocery demand analysis, featuring dimensional modeling and **validated price elasticity estimation**. Built with dbt and PostgreSQL.

**Key Achievement:** Successfully recovered known price elasticities from synthetic data with **~2.4% average error**, validating the log-log regression methodology for application to real vendor data.

## Validation Results

The platform includes a complete elasticity validation pipeline that proves the methodology works before applying it to real data. Using synthetic grocery transactions with known ground-truth elasticities, the log-log regression approach recovers true values with high accuracy.

| Category   | Products | True Elasticity | Estimated | Avg Error |
|------------|----------|-----------------|-----------|-----------|
| Dairy      | 8        | -0.754          | -0.765    | 3.1%      |
| Produce    | 8        | -1.262          | -1.270    | 2.5%      |
| Snacks     | 8        | -2.006          | -2.031    | 1.6%      |
| Beverages  | 8        | -1.442          | -1.458    | 2.4%      |

### Product-Level Validation

![Product-level elasticity validation showing tight clustering along the perfect estimation diagonal](validation_results/product_validation.png)

Product-level estimates show strong correlation with ground truth values across all four categories. Points cluster tightly along the diagonal, confirming unbiased estimation across the full elasticity range.

### Error Distribution

![Distribution of estimation errors centered near zero](validation_results/error_distribution.png)

Errors are centered near zero with most products under 4% error, indicating the methodology produces reliable, unbiased estimates.

### Methodology

**Estimation approach:** Log-log regression per product (Method 2: product-level time series)

```
ln(Q) = β₀ + β₁ × ln(P) + ε
```

where β₁ is the price elasticity estimate. Product-level time series estimation avoids the Simpson's paradox effect that confounds category-level aggregation (Method 1, which fails with 100%+ error on this data).

**Synthetic data generation:** Each product has a known `true_elasticity`. Daily quantities are generated using:

```
Q = base_Q × (P / base_P) ^ elasticity × exp(noise)
```

This embeds the economic relationship into the data so the analysis can attempt to recover it.

**Data:** 280,320 synthetic daily records across 32 products, 12 stores, and 2 years (2023-2024).

## Architecture

### Data Flow

```
generate_data.py → CSVs (data/raw/)
                        ↓
          load_synthetic_data.py → Postgres (raw schema)
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
| Staging | `staging` | view | `stg_` | `stg_synthetic_transactions` |
| Dimensions | `analytics` | table | `dim_` | `dim_synthetic_products` |
| Facts/Marts | `analytics` | table | `fct_`/`mart_` | `fct_synthetic_daily_sales` |

**Note:** dbt prepends the target schema to custom schemas. With target `analytics` and custom schema `analytics`, the actual Postgres schema is `analytics_analytics`.

Two model tracks exist:
- **Synthetic grocery data:** `stg_synthetic_transactions` → `dim_synthetic_products` → `fct_synthetic_daily_sales` → `mart_elasticity_validation` (sources from `raw` schema)
- **Generated/Kaggle data:** `stg_transactions` → `dim_product` → `fact_sales` → `mart_daily_store_performance` (sources from `public` schema, requires Kaggle dataset)

### Airflow Pipeline (Optional)

An Airflow DAG exists for the Kaggle data pipeline but is not required for the core synthetic elasticity workflow.

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- PostgreSQL client (optional, for direct queries)

### Setup

```bash
# Start Postgres warehouse
docker-compose up -d

# Python environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install scipy numpy matplotlib seaborn sqlalchemy setuptools

# Create config/.env
mkdir -p config
cat > config/.env << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=grocery_analytics
DB_USER=analytics_user
DB_PASSWORD=analytics_pass
EOF

# Configure dbt profile (~/.dbt/profiles.yml)
mkdir -p ~/.dbt
cat > ~/.dbt/profiles.yml << 'EOF'
grocery_analytics:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5432
      user: analytics_user
      pass: analytics_pass
      dbname: grocery_analytics
      schema: analytics
      threads: 4
EOF
```

### Run the Pipeline

```bash
source venv/bin/activate

# Generate synthetic data with known elasticities
python3 scripts/generate_data.py

# Load into Postgres
python3 scripts/load_synthetic_data.py

# Run dbt models
cd dbt/grocery_analytics
dbt run --select tag:synthetic tag:elasticity
dbt test --select tag:synthetic

# Run elasticity validation
cd ../..
python3 analysis/demand_analysis.py

# Results output to validation_results/
```

## Project Structure

```
grocery-analytics-platform/
├── analysis/
│   └── demand_analysis.py             # Elasticity estimation & validation
├── config/
│   └── .env                           # Database credentials (gitignored)
├── data/
│   └── raw/                           # Generated CSVs (gitignored)
├── dbt/grocery_analytics/
│   └── models/
│       ├── staging/                   # stg_ views (cleaning/casting)
│       ├── dimensions/                # dim_ tables (products, stores)
│       └── marts/                     # fct_ and mart_ tables (analysis-ready)
├── scripts/
│   ├── generate_data.py               # Synthetic data with demand function
│   ├── load_synthetic_data.py         # Load to Postgres raw schema
│   ├── load_data_to_postgres.py       # Load generated CSVs to public schema
│   ├── fetch_kaggle_inventory.py      # Kaggle dataset download
│   └── load_kaggle_to_postgres.py     # Kaggle data loader
├── validation_results/                # Analysis output
├── docker-compose.yml                 # Postgres warehouse
├── docker-compose-airflow.yml         # Airflow stack (optional)
├── setup_synthetic_data.sh            # Legacy end-to-end setup script
└── requirements.txt
```

## Key Dependencies

`dbt-postgres`, `pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`, `sqlalchemy`, `psycopg2-binary`, `faker`, `python-dotenv`, `setuptools`
