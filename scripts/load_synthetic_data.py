#!/usr/bin/env python3
import os
import pandas as pd
from sqlalchemy import create_engine, text
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
        result = conn.execute(text("SELECT 1"))
        print("✓ Connected to database")
    
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        # Drop dependent dbt views/tables so to_sql can replace raw tables
        conn.execute(text("DROP TABLE IF EXISTS analytics_analytics.mart_elasticity_validation CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS analytics_analytics.fct_synthetic_daily_sales CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS analytics_analytics.dim_synthetic_products CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS analytics_analytics.dim_synthetic_stores CASCADE"))
        conn.execute(text("DROP VIEW IF EXISTS analytics_staging.stg_synthetic_transactions CASCADE"))
        print("✓ Schema ready (cleared dependent objects)")

    print("\nLoading transactions...")
    df = pd.read_csv('data/raw/transactions.csv')
    df.to_sql('synthetic_transactions', engine, schema='raw', 
              if_exists='replace', index=False, chunksize=10000)
    print(f"✓ {len(df):,} transactions loaded")
    
    print("\nLoading products...")
    df = pd.read_csv('data/raw/products.csv')
    df.to_sql('synthetic_products', engine, schema='raw', 
              if_exists='replace', index=False)
    print(f"✓ {len(df)} products loaded")
    
    print("\nLoading stores...")
    df = pd.read_csv('data/raw/stores.csv')
    df.to_sql('synthetic_stores', engine, schema='raw', 
              if_exists='replace', index=False)
    print(f"✓ {len(df)} stores loaded")
    
    print("\n" + "=" * 70)
    print("✓ DATA LOAD COMPLETE!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    sys.exit(1)

