#!/bin/bash
#
# Synthetic Grocery Data Integration Script
# 
# This script:
# 1. Creates the necessary dbt model files
# 2. Loads data to Postgres
# 3. Runs dbt models
# 4. Validates everything worked
#
# Usage: ./setup_synthetic_data.sh

set -e  # Exit on error

# Load environment variables
if [ -f "$(dirname "$0")/.env" ]; then
    set -a; source "$(dirname "$0")/.env"; set +a
elif [ -f ".env" ]; then
    set -a; source ".env"; set +a
fi

PROJECT_ROOT="/Users/travisfowles/grocery-analytics-platform"  # UPDATE THIS!
SYNTHETIC_DATA_DIR="/Users/travisfowles/grocery-analytics-platform/data/raw"  # UPDATE THIS!

echo "=========================================================================="
echo "SYNTHETIC GROCERY DATA INTEGRATION"
echo "=========================================================================="
echo ""

# Check project exists
if [ ! -d "$PROJECT_ROOT" ]; then
    echo "❌ Error: Project directory not found: $PROJECT_ROOT"
    echo "   Please update PROJECT_ROOT in this script"
    exit 1
fi

# Check synthetic data exists
if [ ! -d "$SYNTHETIC_DATA_DIR" ]; then
    echo "❌ Error: Synthetic data directory not found: $SYNTHETIC_DATA_DIR"
    echo "   Please update SYNTHETIC_DATA_DIR in this script"
    exit 1
fi

cd "$PROJECT_ROOT"

echo "✓ Project root: $PROJECT_ROOT"
echo "✓ Synthetic data: $SYNTHETIC_DATA_DIR"
echo ""

# ============================================================================
# STEP 1: Copy Data Files
# ============================================================================
echo "Step 1: Copying data files..."

mkdir -p data/synthetic_grocery

cp "$SYNTHETIC_DATA_DIR/transactions.csv" data/synthetic_grocery/
cp "$SYNTHETIC_DATA_DIR/products.csv" data/synthetic_grocery/
cp "$SYNTHETIC_DATA_DIR/stores.csv" data/synthetic_grocery/

echo "✓ Data files copied"
echo ""

# ============================================================================
# STEP 2: Create Load Script
# ============================================================================
echo "Step 2: Creating load script..."

mkdir -p scripts

cat > scripts/load_synthetic_data.py << 'LOADSCRIPT'
#!/usr/bin/env python3
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import sys

load_dotenv()

DB_HOST = os.environ.get("GROCERY_DB_HOST", "localhost")
DB_PORT = os.environ.get("GROCERY_DB_PORT", "5432")
DB_NAME = os.environ.get("GROCERY_DB_NAME", "grocery_analytics")
DB_USER = os.environ.get("GROCERY_DB_USER", "analytics_user")
DB_PASS = os.environ.get("GROCERY_DB_PASSWORD", "analytics_pass")

conn_string = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print("=" * 70)
print("LOADING SYNTHETIC GROCERY DATA")
print("=" * 70)

try:
    engine = create_engine(conn_string)
    
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("✓ Connected to database")
    
    with engine.connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
        conn.commit()
        print("✓ Schema ready")
    
    print("\nLoading transactions...")
    df = pd.read_csv('data/synthetic_grocery/transactions.csv')
    df.to_sql('synthetic_transactions', engine, schema='raw', 
              if_exists='replace', index=False, chunksize=10000)
    print(f"✓ {len(df):,} transactions loaded")
    
    print("\nLoading products...")
    df = pd.read_csv('data/synthetic_grocery/products.csv')
    df.to_sql('synthetic_products', engine, schema='raw', 
              if_exists='replace', index=False)
    print(f"✓ {len(df)} products loaded")
    
    print("\nLoading stores...")
    df = pd.read_csv('data/synthetic_grocery/stores.csv')
    df.to_sql('synthetic_stores', engine, schema='raw', 
              if_exists='replace', index=False)
    print(f"✓ {len(df)} stores loaded")
    
    print("\n" + "=" * 70)
    print("✓ DATA LOAD COMPLETE!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    sys.exit(1)

LOADSCRIPT

chmod +x scripts/load_synthetic_data.py

echo "✓ Load script created"
echo ""

# ============================================================================
# STEP 3: Load Data to Postgres
# ============================================================================
echo "Step 3: Loading data to Postgres..."
echo "(This may take 1-2 minutes for 434K transactions)"
echo ""

python3 scripts/load_synthetic_data.py

echo ""

# ============================================================================
# STEP 4: Create dbt Source Configuration
# ============================================================================
echo "Step 4: Creating dbt source configuration..."

cat > dbt/models/sources_synthetic.yml << 'SOURCESYML'
version: 2

sources:
  - name: synthetic_grocery
    description: Synthetic grocery data with known elasticities
    database: grocery_analytics
    schema: raw
    tables:
      - name: synthetic_transactions
        description: Daily transaction data (434K records, 2022-2024)
        columns:
          - name: transaction_date
            tests: [not_null]
          - name: store_id
            tests: [not_null]
          - name: upc
            tests: [not_null]
            
      - name: synthetic_products
        description: Product master with true elasticities
        columns:
          - name: upc
            tests: [unique, not_null]
            
      - name: synthetic_stores
        description: Store locations and attributes
        columns:
          - name: store_id
            tests: [unique, not_null]
SOURCESYML

echo "✓ Source configuration created"
echo ""

# ============================================================================
# STEP 5: Create dbt Models
# ============================================================================
echo "Step 5: Creating dbt models..."

# Staging model
mkdir -p dbt/models/staging
cat > dbt/models/staging/stg_synthetic_transactions.sql << 'STAGINGMODEL'
{{ config(materialized='view', tags=['staging', 'synthetic']) }}

WITH source AS (
    SELECT * FROM {{ source('synthetic_grocery', 'synthetic_transactions') }}
),

cleaned AS (
    SELECT
        transaction_date::date AS transaction_date,
        store_id,
        upc,
        units_sold,
        gross_sales,
        cost,
        margin,
        price,
        promotion_flag,
        EXTRACT(YEAR FROM transaction_date) AS year,
        EXTRACT(MONTH FROM transaction_date) AS month,
        EXTRACT(DOW FROM transaction_date) AS day_of_week,
        ROUND(gross_sales / NULLIF(units_sold, 0), 2) AS avg_unit_price,
        ROUND(margin / NULLIF(gross_sales, 0), 4) AS margin_pct,
        CASE WHEN EXTRACT(DOW FROM transaction_date) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend
    FROM source
    WHERE units_sold > 0 AND price > 0
)

SELECT * FROM cleaned
STAGINGMODEL

# Dimension models
mkdir -p dbt/models/dimensions
cat > dbt/models/dimensions/dim_synthetic_products.sql << 'DIMPRODUCTS'
{{ config(materialized='table', tags=['dimension', 'synthetic']) }}

WITH products AS (
    SELECT * FROM {{ source('synthetic_grocery', 'synthetic_products') }}
)

SELECT
    upc,
    product_name,
    category,
    subcategory,
    family,
    organic,
    true_elasticity,
    base_price,
    base_cost,
    ROUND((base_price - base_cost) / NULLIF(base_price, 0), 4) AS base_margin_pct,
    CASE WHEN organic THEN 'Organic' ELSE 'Conventional' END AS organic_type,
    CASE 
        WHEN base_price < 2.00 THEN 'Budget'
        WHEN base_price BETWEEN 2.00 AND 4.99 THEN 'Mid-Tier'
        ELSE 'Premium'
    END AS price_tier
FROM products
DIMPRODUCTS

cat > dbt/models/dimensions/dim_synthetic_stores.sql << 'DIMSTORES'
{{ config(materialized='table', tags=['dimension', 'synthetic']) }}

WITH stores AS (
    SELECT * FROM {{ source('synthetic_grocery', 'synthetic_stores') }}
)

SELECT
    store_id,
    store_name,
    city,
    state,
    region,
    sqft,
    volume_index,
    CASE
        WHEN sqft < 35000 THEN 'Small'
        WHEN sqft BETWEEN 35000 AND 44999 THEN 'Medium'
        ELSE 'Large'
    END AS store_size
FROM stores
DIMSTORES

# Fact table
mkdir -p dbt/models/marts
cat > dbt/models/marts/fct_synthetic_daily_sales.sql << 'FACTMODEL'
{{ config(materialized='table', tags=['fact', 'synthetic']) }}

WITH transactions AS (
    SELECT * FROM {{ ref('stg_synthetic_transactions') }}
),
products AS (
    SELECT * FROM {{ ref('dim_synthetic_products') }}
),
stores AS (
    SELECT * FROM {{ ref('dim_synthetic_stores') }}
)

SELECT
    t.transaction_date,
    t.store_id,
    t.upc,
    s.region,
    s.city,
    p.category,
    p.subcategory,
    p.organic_type,
    p.price_tier,
    t.year,
    t.month,
    t.day_of_week,
    t.is_weekend,
    t.units_sold,
    t.gross_sales,
    t.margin,
    t.price,
    t.promotion_flag,
    t.margin_pct,
    p.true_elasticity,
    p.base_price,
    ROUND(t.price / NULLIF(p.base_price, 0), 4) AS price_index
FROM transactions t
LEFT JOIN products p ON t.upc = p.upc
LEFT JOIN stores s ON t.store_id = s.store_id
FACTMODEL

# Analytics mart
cat > dbt/models/marts/mart_elasticity_validation.sql << 'ELASTICITYMART'
{{ config(materialized='table', tags=['analytics', 'elasticity']) }}

WITH daily_sales AS (
    SELECT * FROM {{ ref('fct_synthetic_daily_sales') }}
),

product_agg AS (
    SELECT
        upc,
        category,
        subcategory,
        organic_type,
        AVG(true_elasticity) AS true_elasticity,
        COUNT(DISTINCT transaction_date) AS days_sold,
        AVG(price) AS avg_price,
        STDDEV(price) AS price_stddev,
        SUM(units_sold) AS total_units,
        AVG(CASE WHEN promotion_flag THEN units_sold END) AS avg_promo_units,
        AVG(CASE WHEN NOT promotion_flag THEN units_sold END) AS avg_regular_units
    FROM daily_sales
    GROUP BY 1, 2, 3, 4
)

SELECT
    *,
    ROUND(price_stddev / NULLIF(avg_price, 0), 4) AS price_cv,
    ROUND((avg_promo_units - avg_regular_units) / NULLIF(avg_regular_units, 0), 4) AS promo_lift,
    CASE 
        WHEN days_sold >= 100 THEN 'Sufficient'
        ELSE 'Insufficient'
    END AS data_quality
FROM product_agg
WHERE days_sold >= 50
ELASTICITYMART

echo "✓ Created 5 dbt model files"
echo ""

# ============================================================================
# STEP 6: Run dbt Models
# ============================================================================
echo "Step 6: Running dbt models..."
echo ""

cd dbt
dbt run --select tag:synthetic

echo ""
echo "✓ dbt models executed"
echo ""

# ============================================================================
# STEP 7: Run dbt Tests
# ============================================================================
echo "Step 7: Running dbt tests..."
echo ""

dbt test --select tag:synthetic

echo ""
echo "✓ dbt tests passed"
echo ""

# ============================================================================
# VERIFICATION
# ============================================================================
echo "=========================================================================="
echo "VERIFICATION"
echo "=========================================================================="
echo ""

# Check row counts
docker exec -i grocery_postgres psql -U "${GROCERY_DB_USER:-analytics_user}" -d "${GROCERY_DB_NAME:-grocery_analytics}" << VERIFYQL
SELECT 
    'Transactions' as table_name,
    COUNT(*) as row_count 
FROM analytics.fct_synthetic_daily_sales
UNION ALL
SELECT 
    'Products',
    COUNT(*) 
FROM analytics.dim_synthetic_products
UNION ALL
SELECT 
    'Stores',
    COUNT(*) 
FROM analytics.dim_synthetic_stores
UNION ALL
SELECT
    'Elasticity Mart',
    COUNT(*)
FROM analytics.mart_elasticity_validation;
VERIFYQL

echo ""
echo "=========================================================================="
echo "✓ INTEGRATION COMPLETE!"
echo "=========================================================================="
echo ""
echo "Next steps:"
echo "1. Check the data: docker exec -it grocery_postgres psql -U analytics_user -d grocery_analytics"
echo "2. Query: SELECT * FROM analytics.mart_elasticity_validation LIMIT 10;"
echo "3. Connect Project 2 to these marts for elasticity analysis"
echo ""
