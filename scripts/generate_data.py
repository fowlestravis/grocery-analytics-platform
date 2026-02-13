import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from faker import Faker
import os

fake = Faker()
np.random.seed(42)
random.seed(42)

# Configuration
NUM_STORES = 12
NUM_DAYS = 365 * 2  # 2 years of daily data
OUTPUT_DIR = 'data/raw'

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Generating synthetic grocery data with known elasticities...")

# === GENERATE PRODUCTS ===
# Each product gets a true_elasticity that the demand function will use.
# Elasticities are negative (law of demand) and vary by category.
print("Generating products...")

categories = {
    'Dairy': {
        'items': ['Whole Milk', '2% Milk', 'Greek Yogurt', 'Cheddar Cheese', 'Butter', 'Cream Cheese', 'Cottage Cheese', 'Sour Cream'],
        'elasticity_range': (-1.0, -0.5),   # Staples: relatively inelastic
        'base_price_range': (2.99, 6.99),
        'base_quantity_range': (80, 200),
    },
    'Produce': {
        'items': ['Bananas', 'Apples', 'Strawberries', 'Avocados', 'Tomatoes', 'Lettuce', 'Broccoli', 'Bell Peppers'],
        'elasticity_range': (-1.5, -0.8),
        'base_price_range': (0.99, 4.99),
        'base_quantity_range': (100, 250),
    },
    'Snacks': {
        'items': ['Potato Chips', 'Pretzels', 'Cookies', 'Crackers', 'Popcorn', 'Trail Mix', 'Granola Bars', 'Candy'],
        'elasticity_range': (-2.5, -1.5),   # Discretionary: more elastic
        'base_price_range': (2.99, 5.99),
        'base_quantity_range': (40, 120),
    },
    'Beverages': {
        'items': ['Orange Juice', 'Cola 12pk', 'Sparkling Water', 'Coffee Beans', 'Green Tea', 'Sports Drink', 'Lemonade', 'Kombucha'],
        'elasticity_range': (-2.0, -1.0),
        'base_price_range': (1.99, 8.99),
        'base_quantity_range': (50, 150),
    },
}

products = []
upc = 100001

for cat_name, cat_info in categories.items():
    for item_name in cat_info['items']:
        true_elasticity = round(np.random.uniform(*cat_info['elasticity_range']), 3)
        base_price = round(np.random.uniform(*cat_info['base_price_range']), 2)
        base_cost = round(base_price * np.random.uniform(0.55, 0.70), 2)
        base_quantity = int(np.random.uniform(*cat_info['base_quantity_range']))

        products.append({
            'upc': upc,
            'product_name': item_name,
            'category': cat_name,
            'subcategory': cat_name,
            'true_elasticity': true_elasticity,
            'base_price': base_price,
            'base_cost': base_cost,
            'base_quantity': base_quantity,
        })
        upc += 1

products_df = pd.DataFrame(products)
products_df.to_csv(f'{OUTPUT_DIR}/products.csv', index=False)
print(f"Generated {len(products_df)} products across {len(categories)} categories")

# === GENERATE STORES ===
print("Generating stores...")

regions = ['Northeast', 'Southeast', 'Midwest', 'West']
stores = []
for store_id in range(1, NUM_STORES + 1):
    region = regions[(store_id - 1) % len(regions)]
    volume_index = round(np.random.uniform(0.7, 1.3), 2)
    sqft = int(np.random.uniform(25000, 55000))

    stores.append({
        'store_id': store_id,
        'store_name': f"{fake.city()} Market",
        'city': fake.city(),
        'state': fake.state_abbr(),
        'region': region,
        'sqft': sqft,
        'volume_index': volume_index,
    })

stores_df = pd.DataFrame(stores)
stores_df.to_csv(f'{OUTPUT_DIR}/stores.csv', index=False)
print(f"Generated {len(stores_df)} stores")

# === DEMAND FUNCTION ===

def generate_demand(base_quantity, price, base_price, elasticity, noise_std=0.15):
    """Generate quantity demanded using the log-log demand model.

    Q = base_Q * (P / base_P) ^ elasticity * exp(noise)
    """
    Q = base_quantity * (price/base_price) ** (elasticity) * np.exp(np.random.normal(0,noise_std))
    Q = max(1,int(Q))
    return Q
    


# === GENERATE TRANSACTIONS ===
print(f"Generating {NUM_DAYS} days of transactions...")

start_date = datetime(2023, 1, 1)
transactions = []

for day in range(NUM_DAYS):
    current_date = start_date + timedelta(days=day)

    # Weekend boost
    is_weekend = current_date.weekday() >= 5
    weekend_factor = 1.15 if is_weekend else 1.0

    for _, store in stores_df.iterrows():
        store_volume = store['volume_index']

        for _, product in products_df.iterrows():
            # Price variation: weekly promotions (~20% of days get a discount)
            promotion = random.random() < 0.20
            if promotion:
                discount = np.random.uniform(0.10, 0.25)
                price = round(product['base_price'] * (1 - discount), 2)
            else:
                # Small random price fluctuations (±3%)
                price = round(product['base_price'] * np.random.uniform(0.97, 1.03), 2)

            # Generate quantity using the demand function
            raw_quantity = generate_demand(
                base_quantity=product['base_quantity'],
                price=price,
                base_price=product['base_price'],
                elasticity=product['true_elasticity'],
            )

            # Scale by store volume and weekend effect
            quantity = max(1, int(raw_quantity * store_volume * weekend_factor))

            transactions.append({
                'transaction_date': current_date.strftime('%Y-%m-%d'),
                'store_id': store['store_id'],
                'upc': product['upc'],
                'units_sold': quantity,
                'price': price,
                'gross_sales': round(price * quantity, 2),
                'cost': round(product['base_cost'] * quantity, 2),
                'margin': round((price - product['base_cost']) * quantity, 2),
                'promotion_flag': promotion,
            })

    if day % 60 == 0:
        print(f"  Generated {day}/{NUM_DAYS} days...")

transactions_df = pd.DataFrame(transactions)
transactions_df.to_csv(f'{OUTPUT_DIR}/transactions.csv', index=False)
print(f"Generated {len(transactions_df):,} daily transaction records")

print("\n=== Data Generation Complete ===")
print(f"Products: {OUTPUT_DIR}/products.csv  ({len(products_df)} products with true elasticities)")
print(f"Stores:   {OUTPUT_DIR}/stores.csv    ({len(stores_df)} stores)")
print(f"Transactions: {OUTPUT_DIR}/transactions.csv ({len(transactions_df):,} records)")
