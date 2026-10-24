"""
generate_demand_curves.py

Generates pre-computed demand curve data for the Tableau pricing tool using the
constant-elasticity power form of the log-log demand model:

    Q(P) = A × P^ε

A is calibrated so that units at the product's average observed price equal its
average daily units. ε defaults to the Method 2 estimated elasticity persisted by
analysis/demand_analysis.py (raw.elasticity_estimates).

Inputs (read from the warehouse using the shared GROCERY_DB_* .env settings):
  analytics_analytics.dim_synthetic_products
  analytics_analytics.mart_elasticity_validation
  raw.elasticity_estimates

Outputs (written to <project root>/exports/):
  mart_demand_curves_v3.csv   — one row per product per price point
  mart_balance_points_v3.csv  — one row per product summary
  mart_elasticity_v3.csv      — clean elasticity table with product names

Usage:
  python3 scripts/generate_demand_curves.py
  python3 scripts/generate_demand_curves.py --elasticity-source true --guardrail 0.15
"""

import argparse
import os

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(PROJECT_ROOT, 'exports')

DEFAULT_GUARDRAIL = 0.20

# Optimum flags, in order of precedence
FLAG_NO_OPTIMUM = 'no_interior_optimum'   # ε ≥ −1: margin rises with price forever
FLAG_GUARDRAIL = 'at_guardrail'           # unconstrained optimum outside the guardrail window
FLAG_EXTRAPOLATED = 'extrapolated'        # inside the guardrail but outside observed prices
FLAG_INTERIOR = 'interior'                # inside the observed price range


# ── Demand model ──────────────────────────────────────────────────────────────

def calibrate_scale(avg_price, avg_units, elasticity):
    """A such that A × avg_price^ε = avg_units."""
    return avg_units / np.power(avg_price, elasticity)


def demand_units(prices, scale, elasticity):
    """Q(P) = A × P^ε"""
    return scale * np.power(prices, elasticity)


def margin(prices, scale, elasticity, cost):
    """Contribution margin: sales − units × cost."""
    units = demand_units(prices, scale, elasticity)
    return units * prices - units * cost


def analytical_optimum(cost, elasticity):
    """Margin-maximizing price cost × ε / (1 + ε); None when ε ≥ −1 (no interior optimum)."""
    if elasticity >= -1:
        return None
    return cost * elasticity / (1 + elasticity)


# ── Price grid ────────────────────────────────────────────────────────────────

def price_grid(lo, hi):
    """Inclusive $0.01 grid from lo to hi, built on integer cents to avoid float drift."""
    lo_c = int(np.ceil(round(lo * 100, 6)))
    hi_c = int(np.floor(round(hi * 100, 6)))
    return np.arange(lo_c, hi_c + 1) / 100.0


def guardrail_window(current_price, cost, guardrail):
    """[current × (1 − g), current × (1 + g)], floored one cent above cost."""
    lo = max(current_price * (1 - guardrail), cost + 0.01)
    hi = current_price * (1 + guardrail)
    return lo, hi


def best_price(prices, scale, elasticity, cost, lo, hi):
    """Grid price in [lo, hi] with the highest margin."""
    mask = (prices >= lo - 1e-9) & (prices <= hi + 1e-9)
    window = prices[mask]
    return float(window[np.argmax(margin(window, scale, elasticity, cost))])


def classify_optimum(unconstrained, guard_lo, guard_hi, obs_lo, obs_hi):
    if unconstrained is None:
        return FLAG_NO_OPTIMUM
    if unconstrained < guard_lo or unconstrained > guard_hi:
        return FLAG_GUARDRAIL
    if unconstrained < obs_lo or unconstrained > obs_hi:
        return FLAG_EXTRAPOLATED
    return FLAG_INTERIOR


# ── Inputs ────────────────────────────────────────────────────────────────────

def load_inputs():
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text

    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    db_host = os.environ.get("GROCERY_DB_HOST", "localhost")
    db_port = os.environ.get("GROCERY_DB_PORT", "5432")
    db_name = os.environ.get("GROCERY_DB_NAME", "grocery_analytics")
    db_user = os.environ.get("GROCERY_DB_USER", "analytics_user")
    db_pass = os.environ["GROCERY_DB_PASSWORD"]
    engine = create_engine(f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

    with engine.begin() as conn:
        dim = pd.read_sql(text("SELECT * FROM analytics_analytics.dim_synthetic_products"), conn)
        elas = pd.read_sql(text("SELECT * FROM analytics_analytics.mart_elasticity_validation"), conn)
        est = pd.read_sql(text("SELECT upc, estimated_elasticity, error_pct FROM raw.elasticity_estimates"), conn)
    return dim, elas, est


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--elasticity-source', choices=['true', 'estimated'], default='estimated',
                        help='ε used for the curves: Method 2 estimate (default) or synthetic ground truth')
    parser.add_argument('--guardrail', type=float, default=DEFAULT_GUARDRAIL,
                        help='max fractional move from current price, g (default 0.20)')
    args = parser.parse_args()

    print("Loading inputs from warehouse...")
    dim, elas, est = load_inputs()
    print(f"  {len(dim)} products, {len(elas)} mart rows, {len(est)} elasticity estimates")

    price_cols = ['upc', 'min_price', 'max_price', 'avg_price',
                  'avg_daily_units', 'avg_regular_price', 'promo_lift',
                  'promo_frequency', 'avg_discount_pct', 'data_quality_flag']
    merged = (dim.merge(elas[price_cols], on='upc', how='left')
                 .merge(est, on='upc', how='left'))

    missing = merged[['min_price', 'estimated_elasticity']].isna().any(axis=1)
    if missing.any():
        raise SystemExit(f"Missing price range or elasticity estimate for UPCs: {merged.loc[missing, 'upc'].tolist()}")

    elasticity_col = 'estimated_elasticity' if args.elasticity_source == 'estimated' else 'true_elasticity'
    print(f"  Using {elasticity_col}, guardrail g = {args.guardrail:.2f}")

    curve_rows = []
    balance_rows = []
    elasticity_rows = []

    for _, row in merged.iterrows():
        upc          = row['upc']
        product_name = row['product_name']
        category     = row['category']
        elast_cat    = row['elasticity_category']
        price_tier   = row['price_tier']
        cost         = float(row['base_cost'])
        base_price   = float(row['base_price'])      # the "current price"
        true_elas    = row['true_elasticity']
        base_margin  = row['base_margin_pct']
        eps          = float(row[elasticity_col])
        scale        = calibrate_scale(float(row['avg_price']), float(row['avg_daily_units']), eps)

        # Observed range and guardrail window, never below cost
        obs_lo = max(float(row['min_price']), cost + 0.01)
        obs_hi = float(row['max_price'])
        guard_lo, guard_hi = guardrail_window(base_price, cost, args.guardrail)

        arp_seq = price_grid(min(obs_lo, guard_lo), max(obs_hi, guard_hi))

        # Demand curve
        units   = demand_units(arp_seq, scale, eps)
        sales   = units * arp_seq
        gig     = sales - (units * cost)
        balance = sales + gig

        # Optimal price points. max_gig_price is the balance point: guardrail-constrained
        max_sales_price    = arp_seq[np.argmax(sales)]
        max_balance_price  = arp_seq[np.argmax(balance)]
        max_gig_price      = best_price(arp_seq, scale, eps, cost, guard_lo, guard_hi)
        observed_gig_price = best_price(arp_seq, scale, eps, cost, obs_lo, obs_hi)
        unconstrained      = analytical_optimum(cost, eps)
        flag = classify_optimum(unconstrained, guard_lo, guard_hi, obs_lo, obs_hi)
        extrapolated = max_gig_price < obs_lo or max_gig_price > obs_hi

        def at_price(p):
            u = demand_units(p, scale, eps)
            s = u * p
            g = s - u * cost
            return u, s, g

        u_base,   s_base,   g_base   = at_price(base_price)
        u_maxgig, s_maxgig, g_maxgig = at_price(max_gig_price)
        _,        _,        g_obs    = at_price(observed_gig_price)

        in_observed = (arp_seq >= obs_lo - 1e-9) & (arp_seq <= obs_hi + 1e-9)
        in_guardrail = (arp_seq >= guard_lo - 1e-9) & (arp_seq <= guard_hi + 1e-9)

        # ── Curve rows ────────────────────────────────────────────────────────
        for i in range(len(arp_seq)):
            curve_rows.append({
                'upc':                  upc,
                'product_name':         product_name,
                'category':             category,
                'elasticity_category':  elast_cat,
                'price_tier':           price_tier,
                'true_elasticity':      true_elas,
                'base_price':           base_price,
                'cost':                 round(cost, 4),
                'arp_seq':              arp_seq[i],
                'units':                round(float(units[i]), 4),
                'sales':                round(float(sales[i]), 4),
                'gig':                  round(float(gig[i]), 4),
                'balance':              round(float(balance[i]), 4),
                'is_base_price':        abs(arp_seq[i] - base_price)      < 0.005,
                'is_max_gig_price':     abs(arp_seq[i] - max_gig_price)   < 0.005,
                'is_max_sales_price':   abs(arp_seq[i] - max_sales_price) < 0.005,
                # New columns
                'elasticity_used':      eps,
                'in_observed_range':    bool(in_observed[i]),
                'in_guardrail_window':  bool(in_guardrail[i]),
                'is_observed_gig_price': abs(arp_seq[i] - observed_gig_price) < 0.005,
            })

        # ── Balance point summary ─────────────────────────────────────────────
        balance_rows.append({
            'upc':                   upc,
            'product_name':          product_name,
            'category':              category,
            'elasticity_category':   elast_cat,
            'price_tier':            price_tier,
            'true_elasticity':       true_elas,
            'base_price':            base_price,
            'cost':                  round(cost, 4),
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
            # New columns
            'elasticity_source':     args.elasticity_source,
            'elasticity_used':       eps,
            'demand_scale_a':        round(float(scale), 6),
            'guardrail_pct':         args.guardrail,
            'guardrail_low_price':   round(guard_lo, 2),
            'guardrail_high_price':  round(guard_hi, 2),
            'observed_min_price':    round(obs_lo, 2),
            'observed_max_price':    round(obs_hi, 2),
            'max_gig_price_observed': round(observed_gig_price, 2),
            'gig_opportunity_observed': round(float(g_obs - g_base), 2),
            'unconstrained_opt_price': None if unconstrained is None else round(unconstrained, 2),
            'optimum_flag':          flag,
            'is_extrapolated':       extrapolated,
        })

        # ── Clean elasticity row ──────────────────────────────────────────────
        elasticity_rows.append({
            'upc':                  upc,
            'product_name':         product_name,
            'category':             category,
            'elasticity_category':  elast_cat,
            'price_tier':           price_tier,
            'true_elasticity':      true_elas,
            'base_price':           base_price,
            'base_cost':            round(cost, 4),
            'base_margin_pct':      float(base_margin),
            'promo_lift':           row['promo_lift'],
            'promo_frequency':      row['promo_frequency'],
            'avg_discount_pct':     row['avg_discount_pct'],
            'data_quality_flag':    row['data_quality_flag'],
            # New columns
            'estimated_elasticity': row['estimated_elasticity'],
            'estimation_error_pct': row['error_pct'],
        })

    # ── Save outputs ──────────────────────────────────────────────────────────
    os.makedirs(EXPORT_DIR, exist_ok=True)
    outputs = {
        'mart_demand_curves_v3.csv':  curve_rows,
        'mart_balance_points_v3.csv': balance_rows,
        'mart_elasticity_v3.csv':     elasticity_rows,
    }
    print("\nOutputs written:")
    for name, rows in outputs.items():
        path = os.path.join(EXPORT_DIR, name)
        pd.DataFrame(rows).to_csv(path, index=False)
        print(f"  {path} → {len(rows):,} rows")

    flags = pd.Series([r['optimum_flag'] for r in balance_rows]).value_counts()
    print("\nOptimum flags:")
    for f, n in flags.items():
        print(f"  {f}: {n}")


if __name__ == '__main__':
    main()
