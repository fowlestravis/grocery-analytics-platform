#!/usr/bin/env python3
import pandas as pd
from sqlalchemy import create_engine, text
import sys

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
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✓ Connected to database")
    
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
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

