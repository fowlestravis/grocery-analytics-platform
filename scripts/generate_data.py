import pandas as pd
import random
from datetime import datetime, timedelta
from faker import Faker
import os

fake = Faker()
random.seed(42)

# Configuration
NUM_STORES = 20
NUM_PRODUCTS = 500
NUM_DAYS = 180
OUTPUT_DIR = 'data/raw'

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Generating grocery retail data...")

# === GENERATE PRODUCTS ===
print("Generating products...")

departments = {
    'Produce': {'categories': ['Organic Produce', 'Conventional Produce', 'Herbs'], 'price_range': (0.99, 8.99), 'perishable': True},
    'Meat & Seafood': {'categories': ['Fresh Meat', 'Poultry', 'Seafood'], 'price_range': (4.99, 29.99), 'perishable': True},
    'Dairy': {'categories': ['Milk & Cream', 'Cheese', 'Yogurt', 'Eggs'], 'price_range': (2.99, 12.99), 'perishable': True},
    'Bakery': {'categories': ['Fresh Bread', 'Pastries', 'Cakes'], 'price_range': (2.99, 15.99), 'perishable': True},
    'Deli': {'categories': ['Prepared Foods', 'Deli Meats', 'Salads'], 'price_range': (5.99, 14.99), 'perishable': True},
    'Frozen': {'categories': ['Frozen Meals', 'Ice Cream', 'Frozen Vegetables'], 'price_range': (3.99, 12.99), 'perishable': False},
    'Grocery': {'categories': ['Canned Goods', 'Pasta & Grains', 'Snacks', 'Beverages'], 'price_range': (1.99, 8.99), 'perishable': False},
    'Health & Beauty': {'categories': ['Personal Care', 'Vitamins', 'Cosmetics'], 'price_range': (3.99, 24.99), 'perishable': False}
}

products = []
sku = 1000

for dept_name, dept_info in departments.items():
    num_in_dept = int(NUM_PRODUCTS * (0.15 if dept_name in ['Produce', 'Grocery'] else 0.10))
    
    for _ in range(num_in_dept):
        category = random.choice(dept_info['categories'])
        price = round(random.uniform(*dept_info['price_range']), 2)
        cost = round(price * random.uniform(0.60, 0.75), 2)
        
        products.append({
            'sku': sku,
            'product_name': f"{fake.word().title()} {category.split()[-1]}",
            'department': dept_name,
            'category': category,
            'price': price,
            'cost': cost,
            'is_perishable': dept_info['perishable']
        })
        sku += 1

products_df = pd.DataFrame(products)
products_df.to_csv(f'{OUTPUT_DIR}/products.csv', index=False)
print(f"Generated {len(products_df)} products")

# === GENERATE STORES ===
print("Generating stores...")

store_formats = ['Large Format', 'Neighborhood Market', 'Urban Express']

stores = []
for store_id in range(1, NUM_STORES + 1):
    store_format = random.choice(store_formats)
    sq_ft = {
        'Large Format': random.randint(45000, 65000),
        'Neighborhood Market': random.randint(25000, 35000),
        'Urban Express': random.randint(10000, 18000)
    }[store_format]
    
    stores.append({
        'store_id': store_id,
        'store_name': f"{fake.city()} {store_format}",
        'city': fake.city(),
        'state': fake.state_abbr(),
        'store_format': store_format,
        'square_footage': sq_ft,
        'opened_date': fake.date_between(start_date='-5y', end_date='-1y')
    })

stores_df = pd.DataFrame(stores)
stores_df.to_csv(f'{OUTPUT_DIR}/stores.csv', index=False)
print(f"Generated {len(stores_df)} stores")

# === GENERATE TRANSACTIONS ===
print("Generating transactions (this may take a minute)...")

start_date = datetime.now() - timedelta(days=NUM_DAYS)
transactions = []
transaction_id = 1000000

basket_weights = [10, 12, 14, 15, 14, 12, 10, 8, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
hour_weights = [5, 6, 7, 6, 5, 8, 10, 12, 15, 18, 20, 18, 15, 12, 8]

for day in range(NUM_DAYS):
    current_date = start_date + timedelta(days=day)
    
    is_weekend = current_date.weekday() >= 5
    base_transactions = 150 if is_weekend else 100
    
    month = current_date.month
    seasonal_factor = 1.2 if month in [5, 6, 7, 11, 12] else 1.0
    
    daily_transactions = int(base_transactions * seasonal_factor)
    
    for store_id in stores_df['store_id']:
        store_transactions = int(daily_transactions / NUM_STORES * random.uniform(0.8, 1.2))
        
        for _ in range(store_transactions):
            hour = random.choices(range(7, 22), weights=hour_weights, k=1)[0]
            minute = random.randint(0, 59)
            transaction_time = current_date.replace(hour=hour, minute=minute)
            
            basket_size = random.choices(range(1, 31), weights=basket_weights, k=1)[0]
            
            basket_products = products_df.sample(n=min(basket_size, len(products_df)))
            
            for _, product in basket_products.iterrows():
                quantity = random.choice([1, 1, 1, 2, 2, 3])
                
                price = product['price']
                if random.random() < 0.15:
                    price = round(price * 0.9, 2)
                
                transactions.append({
                    'transaction_id': transaction_id,
                    'store_id': store_id,
                    'transaction_timestamp': transaction_time,
                    'sku': product['sku'],
                    'quantity': quantity,
                    'price': price
                })
            
            transaction_id += 1
    
    if day % 30 == 0:
        print(f"Generated {day} days of transactions...")

transactions_df = pd.DataFrame(transactions)
transactions_df.to_csv(f'{OUTPUT_DIR}/transactions.csv', index=False)
print(f"Generated {len(transactions_df)} transaction line items")

print("\n=== Data Generation Complete ===")
print(f"Products: {OUTPUT_DIR}/products.csv")
print(f"Stores: {OUTPUT_DIR}/stores.csv")
print(f"Transactions: {OUTPUT_DIR}/transactions.csv")
