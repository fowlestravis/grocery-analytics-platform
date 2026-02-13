import pandas as pd
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/.env')

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

DATA_DIR = 'data/raw'

def create_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ Connected to database successfully")
        return conn
    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        return None

def create_tables(conn):
    """Create raw data tables"""
    cursor = conn.cursor()
    
    # Drop existing tables (for clean reload)
    print("\nDropping existing tables if they exist...")
    cursor.execute("DROP TABLE IF EXISTS raw_transactions CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS raw_products CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS raw_stores CASCADE;")
    
    print("Creating tables...")
    
    # Products table
    cursor.execute("""
        CREATE TABLE raw_products (
            sku INTEGER PRIMARY KEY,
            product_name VARCHAR(255),
            department VARCHAR(100),
            category VARCHAR(100),
            price NUMERIC(10, 2),
            cost NUMERIC(10, 2),
            is_perishable BOOLEAN
        );
    """)
    print("✓ Created raw_products table")
    
    # Stores table
    cursor.execute("""
        CREATE TABLE raw_stores (
            store_id INTEGER PRIMARY KEY,
            store_name VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(2),
            store_format VARCHAR(50),
            square_footage INTEGER,
            opened_date DATE
        );
    """)
    print("✓ Created raw_stores table")
    
    # Transactions table
    cursor.execute("""
        CREATE TABLE raw_transactions (
            transaction_id BIGINT,
            store_id INTEGER,
            transaction_timestamp TIMESTAMP,
            sku INTEGER,
            quantity INTEGER,
            price NUMERIC(10, 2)
        );
    """)
    print("✓ Created raw_transactions table")
    
    conn.commit()
    cursor.close()

def load_csv_to_table(conn, csv_file, table_name):
    """Load CSV data into table"""
    try:
        print(f"\nLoading {csv_file} into {table_name}...")
        
        # Read CSV
        df = pd.read_csv(f"{DATA_DIR}/{csv_file}")
        print(f"  Read {len(df):,} rows from CSV")
        
        # Convert DataFrame to list of tuples
        data = [tuple(row) for row in df.values]
        
        # Create INSERT query
        columns = df.columns.tolist()
        placeholders = ','.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
        
        # Insert data in batches
        cursor = conn.cursor()
        batch_size = 1000
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            cursor.executemany(insert_query, batch)
            
            if (i + batch_size) % 10000 == 0:
                print(f"  Loaded {i + batch_size:,} rows...")
        
        conn.commit()
        cursor.close()
        
        # Verify row count
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.close()
        
        print(f"✓ Loaded {count:,} rows into {table_name}")
        
    except Exception as e:
        print(f"✗ Error loading {csv_file}: {e}")
        conn.rollback()

def main():
    print("=" * 50)
    print("LOADING DATA TO POSTGRES")
    print("=" * 50)
    
    # Connect to database
    conn = create_connection()
    if not conn:
        return
    
    # Create tables
    create_tables(conn)
    
    # Load data
    load_csv_to_table(conn, 'products.csv', 'raw_products')
    load_csv_to_table(conn, 'stores.csv', 'raw_stores')
    load_csv_to_table(conn, 'transactions.csv', 'raw_transactions')
    
    # Close connection
    conn.close()
    
    print("\n" + "=" * 50)
    print("DATA LOAD COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()
