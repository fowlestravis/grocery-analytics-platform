# Exact Integration Steps for YOUR Project

## Your Current Setup (from the YML files)

**Database:**
- Container: `grocery_postgres`
- User: `analytics_user`
- Password: `analytics_pass`
- Database: `grocery_analytics`
- Port: 5432

**dbt Schemas:**
- Staging models → `staging` schema
- Dimension models → `analytics` schema
- Mart models → `analytics` schema

---

## Step 1: Copy Synthetic Data to Your Project

```bash
# Navigate to your project
cd /path/to/grocery-analytics-platform

# Create directory for synthetic data
mkdir -p data/synthetic_grocery

# Copy the files from wherever you downloaded them
cp /path/to/downloads/synthetic_grocery_data/transactions.csv data/synthetic_grocery/
cp /path/to/downloads/synthetic_grocery_data/products.csv data/synthetic_grocery/
cp /path/to/downloads/synthetic_grocery_data/stores.csv data/synthetic_grocery/
```

---

## Step 2: Load Data to Postgres

Create this script: `scripts/load_synthetic_data.py`

```python
#!/usr/bin/env python3
"""
Load synthetic grocery data with known elasticities into Postgres
"""
import pandas as pd
from sqlalchemy import create_engine
import sys

# YOUR database connection (from docker-compose.yml)
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "grocery_analytics"
DB_USER = "analytics_user"
DB_PASS = "analytics_pass"

conn_string = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print("=" * 70)
print("LOADING SYNTHETIC GROCERY DATA")
print("=" * 70)

try:
    engine = create_engine(conn_string)
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("✓ Connected to grocery_analytics database")
    
    # Create raw schema if needed
    with engine.connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
        conn.commit()
        print("✓ Schema 'raw' ready")
    
    # Load transactions
    print("\n1. Loading transactions.csv...")
    df_trans = pd.read_csv('data/synthetic_grocery/transactions.csv')
    print(f"   Read {len(df_trans):,} rows")
    
    df_trans.to_sql(
        'synthetic_transactions',
        engine,
        schema='raw',
        if_exists='replace',
        index=False,
        chunksize=10000
    )
    print(f"   ✓ Loaded to raw.synthetic_transactions")
    
    # Load products
    print("\n2. Loading products.csv...")
    df_products = pd.read_csv('data/synthetic_grocery/products.csv')
    print(f"   Read {len(df_products)} rows")
    
    df_products.to_sql(
        'synthetic_products',
        engine,
        schema='raw',
        if_exists='replace',
        index=False
    )
    print(f"   ✓ Loaded to raw.synthetic_products")
    
    # Load stores
    print("\n3. Loading stores.csv...")
    df_stores = pd.read_csv('data/synthetic_grocery/stores.csv')
    print(f"   Read {len(df_stores)} rows")
    
    df_stores.to_sql(
        'synthetic_stores',
        engine,
        schema='raw',
        if_exists='replace',
        index=False
    )
    print(f"   ✓ Loaded to raw.synthetic_stores")
    
    # Verify
    print("\n" + "=" * 70)
    print("VERIFYING DATA")
    print("=" * 70)
    
    with engine.connect() as conn:
        result = conn.execute("SELECT COUNT(*) FROM raw.synthetic_transactions")
        count = result.fetchone()[0]
        print(f"✓ raw.synthetic_transactions: {count:,} rows")
        
        result = conn.execute("SELECT COUNT(*) FROM raw.synthetic_products")
        count = result.fetchone()[0]
        print(f"✓ raw.synthetic_products: {count} rows")
        
        result = conn.execute("SELECT COUNT(*) FROM raw.synthetic_stores")
        count = result.fetchone()[0]
        print(f"✓ raw.synthetic_stores: {count} rows")
    
    print("\n" + "=" * 70)
    print("✓ DATA LOAD COMPLETE!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Is Docker running? Check: docker ps")
    print("2. Is Postgres container running? Check: docker ps | grep grocery_postgres")
    print("3. Can you connect? Try: docker exec -it grocery_postgres psql -U analytics_user -d grocery_analytics")
    sys.exit(1)

if __name__ == '__main__':
    main()
```

Make it executable and run:
```bash
chmod +x scripts/load_synthetic_data.py
python3 scripts/load_synthetic_data.py
```

Expected output:
```
======================================================================
LOADING SYNTHETIC GROCERY DATA
======================================================================
✓ Connected to grocery_analytics database
✓ Schema 'raw' ready

1. Loading transactions.csv...
   Read 434,016 rows
   ✓ Loaded to raw.synthetic_transactions

2. Loading products.csv...
   Read 33 rows
   ✓ Loaded to raw.synthetic_products

3. Loading stores.csv...
   Read 12 rows
   ✓ Loaded to raw.synthetic_stores

======================================================================
VERIFYING DATA
======================================================================
✓ raw.synthetic_transactions: 434,016 rows
✓ raw.synthetic_products: 33 rows
✓ raw.synthetic_stores: 12 rows

======================================================================
✓ DATA LOAD COMPLETE!
======================================================================
```

---

## Step 3: Verify Data Loaded

```bash
# Connect to your Postgres container
docker exec -it grocery_postgres psql -U analytics_user -d grocery_analytics

# Inside psql, run:
\dt raw.*

# Should show:
#  Schema |         Name          | Type  |     Owner      
# --------+-----------------------+-------+----------------
#  raw    | synthetic_products    | table | analytics_user
#  raw    | synthetic_stores      | table | analytics_user
#  raw    | synthetic_transactions| table | analytics_user

# Check a sample
SELECT COUNT(*) FROM raw.synthetic_transactions;
-- Should return: 434016

# Exit psql
\q
```

---

## Step 4: Add dbt Source Configuration

In your dbt project, add or create `dbt/models/sources.yml`:

```yaml
version: 2

sources:
  # Add this to your existing sources (or create the file if it doesn't exist)
  
  - name: synthetic_grocery
    description: Synthetic grocery data with known elasticities for validation
    database: grocery_analytics
    schema: raw
    tables:
      - name: synthetic_transactions
        description: Daily transaction data (434K records, 2022-2024)
        columns:
          - name: transaction_date
            description: Transaction date
            tests:
              - not_null
          - name: store_id
            description: Store identifier
            tests:
              - not_null
          - name: upc
            description: Product UPC
            tests:
              - not_null
          - name: units_sold
            description: Units sold
            tests:
              - not_null
          - name: price
            description: Unit price
            tests:
              - not_null
            
      - name: synthetic_products
        description: Product master with true elasticities
        columns:
          - name: upc
            description: Product UPC
            tests:
              - unique
              - not_null
          - name: true_elasticity
            description: Known price elasticity (for validation)
            
      - name: synthetic_stores
        description: Store locations and attributes
        columns:
          - name: store_id
            description: Store identifier
            tests:
              - unique
              - not_null
```

---

## Step 5: Create dbt Models

Now create these SQL files in your dbt project:

### File 1: `dbt/models/staging/stg_synthetic_transactions.sql`

```sql
{{
    config(
        materialized='view',
        tags=['staging', 'synthetic']
    )
}}

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
        
        -- Date attributes
        EXTRACT(YEAR FROM transaction_date) AS year,
        EXTRACT(MONTH FROM transaction_date) AS month,
        EXTRACT(QUARTER FROM transaction_date) AS quarter,
        EXTRACT(DOW FROM transaction_date) AS day_of_week,
        TO_CHAR(transaction_date, 'Day') AS day_name,
        
        -- Calculated metrics
        ROUND(gross_sales / NULLIF(units_sold, 0), 2) AS avg_unit_price,
        ROUND(margin / NULLIF(gross_sales, 0), 4) AS margin_pct,
        
        -- Flags
        CASE 
            WHEN EXTRACT(DOW FROM transaction_date) IN (0, 6) THEN TRUE 
            ELSE FALSE 
        END AS is_weekend

    FROM source
    WHERE units_sold > 0 
      AND price > 0
      AND gross_sales > 0
)

SELECT * FROM cleaned
```

### File 2: `dbt/models/dimensions/dim_synthetic_products.sql`

```sql
{{
    config(
        materialized='table',
        tags=['dimension', 'synthetic']
    )
}}

WITH products AS (
    SELECT * FROM {{ source('synthetic_grocery', 'synthetic_products') }}
)

SELECT
    upc,
    product_name,
    subcategory,
    category,
    family,
    organic,
    seasonality,
    base_price,
    base_cost,
    true_elasticity,  -- Key field for validation!
    promotion_frequency,
    
    -- Calculated attributes
    ROUND((base_price - base_cost) / NULLIF(base_price, 0), 4) AS base_margin_pct,
    ROUND(base_price - base_cost, 2) AS base_margin_dollars,
    
    -- Classifications
    CASE
        WHEN organic = TRUE THEN 'Organic'
        ELSE 'Conventional'
    END AS organic_type,
    
    CASE
        WHEN base_price < 2.00 THEN 'Budget'
        WHEN base_price BETWEEN 2.00 AND 4.99 THEN 'Mid-Tier'
        WHEN base_price >= 5.00 THEN 'Premium'
    END AS price_tier,
    
    CASE
        WHEN true_elasticity > -1.0 THEN 'Inelastic'
        WHEN true_elasticity BETWEEN -1.0 AND -1.5 THEN 'Unit Elastic'
        WHEN true_elasticity < -1.5 THEN 'Elastic'
    END AS elasticity_category

FROM products
```

### File 3: `dbt/models/dimensions/dim_synthetic_stores.sql`

```sql
{{
    config(
        materialized='table',
        tags=['dimension', 'synthetic']
    )
}}

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
    
    -- Classifications
    CASE
        WHEN sqft < 35000 THEN 'Small'
        WHEN sqft BETWEEN 35000 AND 44999 THEN 'Medium'
        WHEN sqft >= 45000 THEN 'Large'
    END AS store_size,
    
    CASE
        WHEN volume_index < 1.0 THEN 'Below Average'
        WHEN volume_index = 1.0 THEN 'Average'
        WHEN volume_index BETWEEN 1.0 AND 1.3 THEN 'Above Average'
        WHEN volume_index >= 1.3 THEN 'High Volume'
    END AS volume_tier

FROM stores
```

### File 4: `dbt/models/marts/fct_synthetic_daily_sales.sql`

```sql
{{
    config(
        materialized='table',
        tags=['fact', 'synthetic']
    )
}}

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
    -- Keys
    t.transaction_date,
    t.store_id,
    t.upc,
    
    -- Dimension attributes (for filtering without joins)
    s.region,
    s.city,
    s.state,
    s.store_size,
    s.volume_tier,
    p.category,
    p.subcategory,
    p.family,
    p.organic_type,
    p.price_tier,
    p.elasticity_category,
    p.seasonality,
    
    -- Date attributes
    t.year,
    t.month,
    t.quarter,
    t.day_of_week,
    t.day_name,
    t.is_weekend,
    
    -- Metrics
    t.units_sold,
    t.gross_sales,
    t.cost,
    t.margin,
    t.price,
    t.promotion_flag,
    t.margin_pct,
    
    -- For elasticity validation
    p.true_elasticity,
    p.base_price,
    ROUND(t.price / NULLIF(p.base_price, 0), 4) AS price_index,
    ROUND((t.price - p.base_price) / NULLIF(p.base_price, 0), 4) AS price_variance_pct

FROM transactions t
LEFT JOIN products p ON t.upc = p.upc
LEFT JOIN stores s ON t.store_id = s.store_id
```

### File 5: `dbt/models/marts/mart_elasticity_validation.sql`

```sql
{{
    config(
        materialized='table',
        tags=['analytics', 'elasticity']
    )
}}

-- This mart prepares data for elasticity analysis and validation
WITH daily_sales AS (
    SELECT * FROM {{ ref('fct_synthetic_daily_sales') }}
),

product_aggregates AS (
    SELECT
        upc,
        category,
        subcategory,
        organic_type,
        elasticity_category,
        
        -- Ground truth
        AVG(true_elasticity) AS true_elasticity,
        AVG(base_price) AS base_price,
        
        -- Volume metrics
        COUNT(DISTINCT transaction_date) AS days_sold,
        SUM(units_sold) AS total_units_sold,
        AVG(units_sold) AS avg_daily_units,
        
        -- Price metrics (needed for elasticity estimation)
        AVG(price) AS avg_price,
        STDDEV(price) AS price_stddev,
        MIN(price) AS min_price,
        MAX(price) AS max_price,
        
        -- Promotional metrics
        SUM(CASE WHEN promotion_flag THEN 1 ELSE 0 END)::FLOAT / 
            NULLIF(COUNT(*), 0) AS promo_frequency,
        
        AVG(CASE WHEN promotion_flag THEN units_sold END) AS avg_promo_units,
        AVG(CASE WHEN NOT promotion_flag THEN units_sold END) AS avg_regular_units,
        
        AVG(CASE WHEN promotion_flag THEN price END) AS avg_promo_price,
        AVG(CASE WHEN NOT promotion_flag THEN price END) AS avg_regular_price
        
    FROM daily_sales
    GROUP BY 1, 2, 3, 4, 5
)

SELECT
    *,
    
    -- Derived metrics
    ROUND(price_stddev / NULLIF(avg_price, 0), 4) AS price_coefficient_variation,
    ROUND((max_price - min_price) / NULLIF(avg_price, 0), 4) AS price_range_pct,
    ROUND((avg_promo_units - avg_regular_units) / NULLIF(avg_regular_units, 0), 4) AS promo_lift,
    ROUND((avg_regular_price - avg_promo_price) / NULLIF(avg_regular_price, 0), 4) AS avg_discount_pct,
    
    -- Data quality flags
    CASE 
        WHEN days_sold >= 100 AND price_stddev > 0 THEN 'Sufficient Data'
        WHEN days_sold < 100 THEN 'Insufficient Observations'
        WHEN price_stddev = 0 THEN 'No Price Variation'
        ELSE 'Check Data'
    END AS data_quality_flag

FROM product_aggregates
WHERE days_sold >= 50  -- Only include products with sufficient history
```

---

## Step 6: Run dbt Models

```bash
cd dbt

# Run just the synthetic models
dbt run --select tag:synthetic

# You should see:
# Running with dbt=1.x.x
# Found 5 models, X tests, 0 snapshots, 0 analyses
#
# Concurrency: 4 threads (target='dev')
#
# 1 of 5 START sql view model staging.stg_synthetic_transactions .... [RUN]
# 1 of 5 OK created sql view model staging.stg_synthetic_transactions [CREATE VIEW in 0.50s]
# 2 of 5 START sql table model analytics.dim_synthetic_products ....... [RUN]
# 3 of 5 START sql table model analytics.dim_synthetic_stores ......... [RUN]
# 2 of 5 OK created sql table model analytics.dim_synthetic_products .. [CREATE 33 in 0.23s]
# 3 of 5 OK created sql table model analytics.dim_synthetic_stores .... [CREATE 12 in 0.18s]
# 4 of 5 START sql table model analytics.fct_synthetic_daily_sales .... [RUN]
# 4 of 5 OK created sql table model analytics.fct_synthetic_daily_sales [CREATE 434016 in 2.45s]
# 5 of 5 START sql table model analytics.mart_elasticity_validation ... [RUN]
# 5 of 5 OK created sql table model analytics.mart_elasticity_validation [CREATE 33 in 0.67s]
#
# Finished running 1 view model, 4 table models in 0 hours 0 minutes and 4.03 seconds (4.03s).
#
# Completed successfully
```

---

## Step 7: Run dbt Tests

```bash
dbt test --select tag:synthetic

# Should see:
# Running with dbt=1.x.x
# Found X tests
# 
# 1 of X START test not_null_synthetic_transactions_transaction_date .. [RUN]
# 1 of X PASS not_null_synthetic_transactions_transaction_date ........ [PASS in 0.15s]
# ...
# Completed successfully
```

---

## Step 8: Verify in Postgres

```bash
docker exec -it grocery_postgres psql -U analytics_user -d grocery_analytics
```

Inside psql:
```sql
-- Check schemas
\dn

-- Check tables
\dt analytics.*

-- Verify data
SELECT 
    category,
    COUNT(DISTINCT upc) as products,
    ROUND(AVG(true_elasticity), 2) as avg_true_elasticity,
    ROUND(AVG(price_coefficient_variation), 2) as avg_price_cv
FROM analytics.mart_elasticity_validation
WHERE data_quality_flag = 'Sufficient Data'
GROUP BY 1;

-- Should see:
--  category   | products | avg_true_elasticity | avg_price_cv 
-- ------------+----------+---------------------+--------------
--  Fruit      |       20 |               -1.44 |         0.06
--  Vegetables |       13 |               -1.04 |         0.06
```

---

## Success! ✓

You now have:
- [x] Synthetic data loaded to Postgres
- [x] dbt models creating staging → dimensions → fact → analytics layers
- [x] Ground truth elasticities available for validation
- [x] Ready to run elasticity analysis

---

## Next: Connect to Demand Analysis

Now update your `demand_analysis_synthetic.py` to query from these marts:

```python
from sqlalchemy import create_engine

# Connect to YOUR database
engine = create_engine('postgresql://analytics_user:analytics_pass@localhost:5432/grocery_analytics')

# Query the validation mart
query = """
SELECT 
    upc,
    category,
    true_elasticity,
    avg_price,
    price_coefficient_variation,
    promo_frequency,
    data_quality_flag
FROM analytics.mart_elasticity_validation
WHERE data_quality_flag = 'Sufficient Data'
"""

products = pd.read_sql(query, engine)

# Now run elasticity analysis and validate!
for _, product in products.iterrows():
    # Your analysis code...
    pass
```

---

## Troubleshooting

**If load script fails:**
```bash
# Check Docker is running
docker ps

# Check you can connect
docker exec -it grocery_postgres psql -U analytics_user -d grocery_analytics
```

**If dbt fails:**
```bash
# Check connection
cd dbt
dbt debug

# Run with verbose output
dbt run --select tag:synthetic --debug
```

Let me know when you're ready to run this!
