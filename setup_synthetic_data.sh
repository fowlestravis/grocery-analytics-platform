#!/bin/bash
#
# Synthetic Grocery Data Setup Script
#
# Orchestrates the full synthetic data pipeline using existing scripts
# and dbt models. Safe to re-run — does not overwrite model files.
#
# Prerequisites:
#   - .env file at project root (copy from .env.example)
#   - Docker containers running (docker-compose up -d)
#   - Python venv activated with requirements installed
#
# Usage: ./setup_synthetic_data.sh

set -e  # Exit on error

# Load environment variables
if [ -f "$(dirname "$0")/.env" ]; then
    set -a; source "$(dirname "$0")/.env"; set +a
elif [ -f ".env" ]; then
    set -a; source ".env"; set +a
fi

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================================================="
echo "SYNTHETIC GROCERY DATA SETUP"
echo "=========================================================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# ============================================================================
# STEP 1: Generate Synthetic Data
# ============================================================================
echo "Step 1: Generating synthetic data..."
python3 scripts/generate_data.py
echo ""
echo "✓ Data generated in data/raw/"
echo ""

# ============================================================================
# STEP 2: Load Data to Postgres
# ============================================================================
echo "Step 2: Loading data to Postgres..."
python3 scripts/load_synthetic_data.py
echo ""

# ============================================================================
# STEP 3: Run dbt Models
# ============================================================================
echo "Step 3: Running dbt models..."
echo ""
cd dbt/grocery_analytics
dbt run --select tag:synthetic tag:elasticity
echo ""
echo "✓ dbt models executed"
echo ""

# ============================================================================
# STEP 4: Run dbt Tests
# ============================================================================
echo "Step 4: Running dbt tests..."
echo ""
dbt test --select tag:synthetic tag:elasticity
echo ""
echo "✓ dbt tests passed"
echo ""

# ============================================================================
# VERIFICATION
# ============================================================================
cd "$PROJECT_ROOT"

echo "=========================================================================="
echo "VERIFICATION"
echo "=========================================================================="
echo ""

docker exec -i grocery_postgres psql \
    -U "${GROCERY_DB_USER:-analytics_user}" \
    -d "${GROCERY_DB_NAME:-grocery_analytics}" << 'VERIFYQL'
SELECT
    'dim_synthetic_products' AS table_name, COUNT(*) AS row_count
    FROM analytics_analytics.dim_synthetic_products
UNION ALL
SELECT 'dim_synthetic_stores', COUNT(*)
    FROM analytics_analytics.dim_synthetic_stores
UNION ALL
SELECT 'fct_synthetic_daily_sales', COUNT(*)
    FROM analytics_analytics.fct_synthetic_daily_sales
UNION ALL
SELECT 'mart_elasticity_validation', COUNT(*)
    FROM analytics_analytics.mart_elasticity_validation;
VERIFYQL

echo ""
echo "=========================================================================="
echo "✓ SETUP COMPLETE"
echo "=========================================================================="
echo ""
echo "Next steps:"
echo "  docker exec -it grocery_postgres psql -U analytics_user -d grocery_analytics"
echo "  SELECT * FROM analytics_analytics.mart_elasticity_validation LIMIT 10;"
echo ""
