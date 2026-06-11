"""
generate_demand_curves_v3.py

Generates pre-computed demand curve data using the enriched product dimension
as the master table. Uses real product names, real base_cost, and true
elasticity values from dim_synthetic_products.

Outputs:
  mart_demand_curves_v3.csv   — one row per product per price point
  mart_balance_points_v3.csv  — one row per product summary
  mart_elasticity_v3.csv      — clean elasticity table with product names

Usage:
  Place these two files in the same directory as this script, then run:
    python3 generate_demand_curves_v3.py

  Required input files:
    dim_products_enriched.csv          (exported from dim_synthetic_products)
    mart_elasticity_validation.csv     (exported from mart_elasticity_validation)
"""

import pandas as pd
import numpy as np

# ── Load inputs ───────────────────────────────────────────────────────────────
print("Loading enriched product dimension...")
dim = pd.read_csv("dim_products_enriched.csv")
print(f"  {len(dim)} products")
print(f"  Categories: {sorted(dim['category'].unique())}")

print("\nLoading elasticity mart for observed price ranges...")
elas = pd.read_csv("mart_elasticity_validation.csv")
print(f"  {len(elas)} products")

# Merge observed price ranges from elasticity mart into dim
# dim has true_elasticity and base_cost already — we just need
# min_price, max_price, avg_daily_units, avg_price from the mart
price_cols = ['upc', 'min_price', 'max_price', 'avg_price',
              'avg_daily_units', 'avg_regular_price', 'promo_lift',
              'promo_frequency', 'avg_discount_pct', 'data_quality_flag']

merged = dim.merge(elas[price_cols], on='upc', how='left')

missing = merged['min_price'].isna().sum()
if missing > 0:
    print(f"  WARNING: {missing} products missing price range data")

print(f"\nSample enriched product data:")
print(merged[['upc', 'product_name', 'category', 'base_cost',
              'true_elasticity', 'base_price', 'avg_price']].head(5).to_string(index=False))

# ── Derive b_intercept_exp ────────────────────────────────────────────────────
# ln(units) = b_intercept + b_ARP * price
# At avg_price: avg_daily_units = b_intercept_exp * exp(b_ARP * avg_price)
# Therefore:   b_intercept_exp = avg_daily_units / exp(b_ARP * avg_price)

merged['b_ARP'] = merged['true_elasticity']
merged['b_intercept_exp'] = (
    merged['avg_daily_units'] / np.exp(merged['b_ARP'] * merged['avg_price'])
)

# ── Generate demand curves ────────────────────────────────────────────────────
print("\nGenerating demand curves...")

curve_rows   = []
balance_rows = []
elasticity_rows = []

for _, row in merged.iterrows():
    upc          = row['upc']
    product_name = row['product_name']
    category     = row['category']
    elast_cat    = row['elasticity_category']
    price_tier   = row['price_tier']
    b_ARP        = row['b_ARP']
    b_int_exp    = row['b_intercept_exp']
    cost         = row['base_cost']          # real cost from dim
    base_price   = row['base_price']
    true_elas    = row['true_elasticity']
    base_margin  = row['base_margin_pct']

    # Price sequence: $0.01 steps, never price below cost
    min_p   = max(row['min_price'], cost + 0.01)
    max_p   = row['max_price']
    arp_seq = np.round(np.arange(min_p, max_p, 0.01), 2)

    # Demand curve
    units   = b_int_exp * np.exp(b_ARP * arp_seq)
    sales   = units * arp_seq
    gig     = sales - (units * cost)
    balance = sales + gig

    # Optimal price points
    max_sales_price   = arp_seq[np.argmax(sales)]
    max_gig_price     = arp_seq[np.argmax(gig)]
    max_balance_price = arp_seq[np.argmax(balance)]

    def at_price(p):
        u = b_int_exp * np.exp(b_ARP * p)
        s = u * p
        g = s - u * cost
        return u, s, g

    u_base,   s_base,   g_base   = at_price(base_price)
    u_maxgig, s_maxgig, g_maxgig = at_price(max_gig_price)

    # ── Curve rows ────────────────────────────────────────────────────────────
    for i in range(len(arp_seq)):
        curve_rows.append({
            'upc':                  upc,
            'product_name':         product_name,
            'category':             category,
            'elasticity_category':  elast_cat,
            'price_tier':           price_tier,
            'true_elasticity':      true_elas,
            'base_price':           base_price,
            'cost':                 round(float(cost), 4),
            'arp_seq':              arp_seq[i],
            'units':                round(float(units[i]), 4),
            'sales':                round(float(sales[i]), 4),
            'gig':                  round(float(gig[i]), 4),
            'balance':              round(float(balance[i]), 4),
            'is_base_price':        abs(arp_seq[i] - base_price)     < 0.005,
            'is_max_gig_price':     abs(arp_seq[i] - max_gig_price)  < 0.005,
            'is_max_sales_price':   abs(arp_seq[i] - max_sales_price) < 0.005,
        })

    # ── Balance point summary ─────────────────────────────────────────────────
    balance_rows.append({
        'upc':                   upc,
        'product_name':          product_name,
        'category':              category,
        'elasticity_category':   elast_cat,
        'price_tier':            price_tier,
        'true_elasticity':       true_elas,
        'base_price':            base_price,
        'cost':                  round(float(cost), 4),
        'base_margin_pct':       float(base_margin),
        'max_sales_price':       round(float(max_sales_price), 2),
        'max_gig_price':         round(float(max_gig_price), 2),
        'max_balance_price':     round(float(max_balance_price), 2),
        'price_gap_to_max_gig':  round(float(base_price - max_gig_price), 2),
        'price_gap_to_max_sales':round(float(base_price - max_sales_price), 2),
        'units_at_base':         round(float(u_base), 2),
        'sales_at_base':         round(float(s_base), 2),
        'gig_at_base':           round(float(g_base), 2),
        'units_at_max_gig':      round(float(u_maxgig), 2),
        'sales_at_max_gig':      round(float(s_maxgig), 2),
        'gig_at_max_gig':        round(float(g_maxgig), 2),
        'gig_opportunity':       round(float(g_maxgig - g_base), 2),
    })

    # ── Clean elasticity row ──────────────────────────────────────────────────
    elasticity_rows.append({
        'upc':                  upc,
        'product_name':         product_name,
        'category':             category,
        'elasticity_category':  elast_cat,
        'price_tier':           price_tier,
        'true_elasticity':      true_elas,
        'base_price':           base_price,
        'base_cost':            round(float(cost), 4),
        'base_margin_pct':      float(base_margin),
        'promo_lift':           row['promo_lift'],
        'promo_frequency':      row['promo_frequency'],
        'avg_discount_pct':     row['avg_discount_pct'],
        'data_quality_flag':    row['data_quality_flag'],
    })

# ── Save outputs ──────────────────────────────────────────────────────────────
pd.DataFrame(curve_rows).to_csv('mart_demand_curves_v3.csv',   index=False)
pd.DataFrame(balance_rows).to_csv('mart_balance_points_v3.csv', index=False)
pd.DataFrame(elasticity_rows).to_csv('mart_elasticity_v3.csv',  index=False)

print(f"\nOutputs written:")
print(f"  mart_demand_curves_v3.csv   → {len(curve_rows):,} rows")
print(f"  mart_balance_points_v3.csv  → {len(balance_rows)} rows")
print(f"  mart_elasticity_v3.csv      → {len(elasticity_rows)} rows")
print(f"\nReplace your existing Tableau data sources with these three files.")
print(f"  - mart_elasticity_v3.csv     replaces mart_elasticity_validation.csv")
print(f"  - mart_demand_curves_v3.csv  replaces mart_demand_curves.csv")
print(f"  - mart_balance_points_v3.csv replaces mart_balance_points.csv")
print(f"\nKey improvements over v2:")
print(f"  - Real product names instead of UPC codes")
print(f"  - Real base_cost from dim_synthetic_products (not estimated)")
print(f"  - price_tier field enables additional segmentation")
print(f"  - Clean elasticity table ready for Tableau hierarchy")
