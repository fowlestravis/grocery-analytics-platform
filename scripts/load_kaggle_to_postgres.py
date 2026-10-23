import pandas as pd
import psycopg2
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('GROCERY_DB_HOST', 'localhost'),
    'port': os.getenv('GROCERY_DB_PORT', '5432'),
    'database': os.getenv('GROCERY_DB_NAME', 'grocery_analytics'),
    'user': os.getenv('GROCERY_DB_USER', 'analytics_user'),
    'password': os.getenv('GROCERY_DB_PASSWORD', 'analytics_pass')
}

CSV_FILE = 'data/kaggle/Grocery_Inventory new v1.csv'


def create_connection():
    """Create database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Connected to database successfully")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def create_table(conn):
    """Create raw_inventory table."""
    cursor = conn.cursor()

    logger.info("Dropping existing raw_inventory table if it exists...")
    cursor.execute("DROP TABLE IF EXISTS raw_inventory CASCADE;")

    logger.info("Creating raw_inventory table...")
    cursor.execute("""
        CREATE TABLE raw_inventory (
            product_name VARCHAR(255),
            category VARCHAR(100),
            supplier_name VARCHAR(255),
            warehouse_location VARCHAR(255),
            status VARCHAR(50),
            product_id VARCHAR(50),
            supplier_id VARCHAR(50),
            date_received DATE,
            last_order_date DATE,
            expiration_date DATE,
            stock_quantity INTEGER,
            reorder_level INTEGER,
            reorder_quantity INTEGER,
            unit_price NUMERIC(10, 2),
            sales_volume INTEGER,
            inventory_turnover_rate INTEGER,
            percentage NUMERIC(5, 2)
        );
    """)

    conn.commit()
    cursor.close()
    logger.info("Created raw_inventory table")


def clean_price(value):
    """Remove $ prefix from price values."""
    if pd.isna(value):
        return None
    return float(str(value).replace('$', '').replace(',', ''))


def clean_percentage(value):
    """Remove % suffix from percentage values."""
    if pd.isna(value):
        return None
    return float(str(value).replace('%', ''))


def parse_date(value):
    """Parse date values, returning None for invalid dates."""
    if pd.isna(value):
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def load_csv_to_table(conn):
    """Load CSV data into raw_inventory table."""
    logger.info(f"Loading {CSV_FILE} into raw_inventory...")

    # Read CSV
    df = pd.read_csv(CSV_FILE)
    logger.info(f"Read {len(df):,} rows from CSV")

    # Rename columns to match database schema (note: source has typo "Catagory")
    df.columns = [
        'product_name', 'category', 'supplier_name', 'warehouse_location',
        'status', 'product_id', 'supplier_id', 'date_received',
        'last_order_date', 'expiration_date', 'stock_quantity',
        'reorder_level', 'reorder_quantity', 'unit_price', 'sales_volume',
        'inventory_turnover_rate', 'percentage'
    ]

    # Clean data
    df['unit_price'] = df['unit_price'].apply(clean_price)
    df['percentage'] = df['percentage'].apply(clean_percentage)
    df['date_received'] = df['date_received'].apply(parse_date)
    df['last_order_date'] = df['last_order_date'].apply(parse_date)
    df['expiration_date'] = df['expiration_date'].apply(parse_date)

    # Convert DataFrame to list of tuples
    data = [tuple(None if pd.isna(x) else x for x in row) for row in df.values]

    # Create INSERT query
    columns = df.columns.tolist()
    placeholders = ','.join(['%s'] * len(columns))
    insert_query = f"INSERT INTO raw_inventory ({','.join(columns)}) VALUES ({placeholders})"

    # Insert data in batches
    cursor = conn.cursor()
    batch_size = 1000

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany(insert_query, batch)

        if (i + batch_size) % 10000 == 0:
            logger.info(f"Loaded {i + batch_size:,} rows...")

    conn.commit()
    cursor.close()

    # Verify row count
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM raw_inventory")
    count = cursor.fetchone()[0]
    cursor.close()

    logger.info(f"Loaded {count:,} rows into raw_inventory")


def main():
    """Main function to orchestrate the data load."""
    logger.info("=" * 50)
    logger.info("LOADING KAGGLE INVENTORY DATA TO POSTGRES")
    logger.info("=" * 50)

    try:
        # Check if CSV file exists
        if not os.path.exists(CSV_FILE):
            raise FileNotFoundError(f"CSV file not found: {CSV_FILE}")

        # Connect to database
        conn = create_connection()

        # Create table
        create_table(conn)

        # Load data
        load_csv_to_table(conn)

        # Close connection
        conn.close()

        logger.info("=" * 50)
        logger.info("DATA LOAD COMPLETE")
        logger.info("=" * 50)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
