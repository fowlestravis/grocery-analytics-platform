"""
Set up Metabase dashboard for Grocery Analytics via the Metabase API.

Idempotent: finds existing cards/dashboards by name and updates them,
or creates new ones if they don't exist. Safe to re-run.

Creates/updates 10 cards on a single dashboard:
  1. Total Products (KPI)
  2. Total Transactions (KPI)
  3. Data Freshness (KPI)
  4. Sales by Category (bar chart)
  5. True vs Estimated Elasticity (scatter plot)
  6. Daily Sales Trend (line chart)
  7. Avg Validation Error % (big number)
  8. Demand Curves: Price vs Quantity (line chart)
  9. Demand Curves: Log-Log (line chart)
  10. Demand Curve Interactive (line chart with category/product filters)

Usage:
  python scripts/setup_metabase_dashboard.py            # create or update
  python scripts/setup_metabase_dashboard.py --dry-run   # preview without writing
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

MB_URL = os.environ.get("METABASE_URL", "http://localhost:3000")
MB_EMAIL = os.environ.get("METABASE_EMAIL")
MB_PASS = os.environ.get("METABASE_PASSWORD")

DRY_RUN = False


def get_session():
    resp = requests.post(f"{MB_URL}/api/session", json={
        "username": MB_EMAIL, "password": MB_PASS
    })
    resp.raise_for_status()
    return resp.json()["id"]


def api(session, method, path, **kwargs):
    headers = {"X-Metabase-Session": session}
    resp = getattr(requests, method)(f"{MB_URL}{path}", headers=headers, **kwargs)
    resp.raise_for_status()
    return resp.json() if resp.text else None


def find_database(session):
    dbs = api(session, "get", "/api/database")
    for db in dbs.get("data", dbs):
        if db["name"] == "Grocery Analytics":
            return db["id"]
    raise RuntimeError("Grocery Analytics database not found in Metabase")


def find_cards_by_name(session, name):
    """Find active (non-archived) cards matching an exact name."""
    all_cards = api(session, "get", "/api/card")
    return [c for c in all_cards
            if c["name"] == name and not c.get("archived")]


def find_dashboard_by_name(session, name):
    """Find dashboards matching an exact name."""
    dashboards = api(session, "get", "/api/dashboard")
    return [d for d in dashboards if d["name"] == name]


def upsert_native_card(session, name, db_id, sql, display="scalar",
                       viz_settings=None, template_tags=None):
    """Find card by name and update it, or create a new one.

    If multiple active cards share the same name, stop and list duplicates.
    """
    matches = find_cards_by_name(session, name)

    if len(matches) > 1:
        print(f"\n  ERROR: {len(matches)} active cards named {name!r}:")
        for m in matches:
            print(f"    id={m['id']}  collection={m.get('collection_id')}"
                  f"  created={m['created_at'][:10]}")
        sys.exit(1)

    native_block = {"query": sql}
    if template_tags:
        native_block["template-tags"] = template_tags

    payload = {
        "name": name,
        "dataset_query": {
            "type": "native",
            "native": native_block,
            "database": db_id,
        },
        "display": display,
        "visualization_settings": viz_settings or {},
    }

    if matches:
        card_id = matches[0]["id"]
        if DRY_RUN:
            print(f"  [dry-run] Would UPDATE card id={card_id}: {name!r}")
        else:
            api(session, "put", f"/api/card/{card_id}", json=payload)
            print(f"  UPDATED card id={card_id}: {name!r}")
        return card_id
    else:
        if DRY_RUN:
            print(f"  [dry-run] Would CREATE card: {name!r}")
            return -1  # placeholder
        else:
            card = api(session, "post", "/api/card", json=payload)
            print(f"  CREATED card id={card['id']}: {name!r}")
            return card["id"]


def upsert_dashboard(session, name, description):
    """Find dashboard by name and return its id, or create a new one."""
    matches = find_dashboard_by_name(session, name)

    if len(matches) > 1:
        print(f"\n  ERROR: {len(matches)} dashboards named {name!r}:")
        for m in matches:
            print(f"    id={m['id']}  collection={m.get('collection_id')}")
        sys.exit(1)

    if matches:
        dash_id = matches[0]["id"]
        if DRY_RUN:
            print(f"  [dry-run] Would UPDATE dashboard id={dash_id}: {name!r}")
        else:
            api(session, "put", f"/api/dashboard/{dash_id}", json={
                "name": name, "description": description,
            })
            print(f"  UPDATED dashboard id={dash_id}: {name!r}")
        return dash_id
    else:
        if DRY_RUN:
            print(f"  [dry-run] Would CREATE dashboard: {name!r}")
            return -1
        else:
            dashboard = api(session, "post", "/api/dashboard", json={
                "name": name, "description": description,
            })
            print(f"  CREATED dashboard id={dashboard['id']}: {name!r}")
            return dashboard["id"]


# ── Card definitions ────────────────────────────────────────────────

DEMAND_CURVE_SQL = """
    WITH selected_products AS (
        SELECT upc, product_name, category, true_elasticity
        FROM analytics_analytics.dim_synthetic_products
        WHERE product_name IN ('Cheddar Cheese', 'Tomatoes', 'Potato Chips', 'Sparkling Water','Coffee Beans')
    ),
    binned AS (
        SELECT
            p.product_name,
            p.true_elasticity,
            s.price,
            s.units_sold,
            NTILE(20) OVER (PARTITION BY s.upc ORDER BY s.price) AS price_bin
        FROM analytics_analytics.fct_synthetic_daily_sales s
        JOIN selected_products p ON s.upc = p.upc
        WHERE s.price > 0 AND s.units_sold > 0
    )
    SELECT
        product_name || ' (e=' || ROUND(true_elasticity::numeric, 2) || ')' AS product,
        ROUND(AVG(price)::numeric, 2) AS avg_price,
        ROUND(AVG(units_sold)::numeric, 1) AS avg_quantity
    FROM binned
    GROUP BY product_name, true_elasticity, price_bin
    ORDER BY product_name, avg_price
"""

LOG_DEMAND_SQL = DEMAND_CURVE_SQL.replace(
    "ROUND(AVG(price)::numeric, 2) AS avg_price",
    "ROUND(LN(AVG(price))::numeric, 3) AS ln_price"
).replace(
    "ROUND(AVG(units_sold)::numeric, 1) AS avg_quantity",
    "ROUND(LN(AVG(units_sold))::numeric, 3) AS ln_quantity"
).replace(
    "ORDER BY product_name, avg_price",
    "ORDER BY product_name, ln_price"
)

INTERACTIVE_DEMAND_SQL = """
WITH selected_products AS (
    SELECT upc, product_name, category, true_elasticity
    FROM analytics_analytics.dim_synthetic_products
    WHERE {{category}} AND {{product}}
),
binned AS (
    SELECT
        p.product_name || ' (e=' || ROUND(p.true_elasticity::numeric, 2) || ')' AS product,
        s.price,
        s.units_sold,
        NTILE(20) OVER (PARTITION BY s.upc ORDER BY s.price) AS price_bin
    FROM analytics_analytics.fct_synthetic_daily_sales s
    JOIN selected_products p ON s.upc = p.upc
    WHERE s.price > 0 AND s.units_sold > 0
)
SELECT
    price_bin AS bin,
    product,
    ROUND(AVG(price)::numeric, 2) AS price,
    ROUND(AVG(units_sold)::numeric, 1) AS quantity
FROM binned
GROUP BY price_bin, product
ORDER BY product, price_bin
"""

# Metabase field filter template tags for the interactive card.
# Field IDs are Metabase-internal references to dim_synthetic_products columns.
# See CLAUDE.md "Metabase field IDs for filters" for current values.
INTERACTIVE_TEMPLATE_TAGS = {
    "category": {
        "id": "category_filter",
        "name": "category",
        "display-name": "Category",
        "type": "dimension",
        "widget-type": "string/=",
        "dimension": ["field", 106, None],
        "default": None,
    },
    "product": {
        "id": "product_filter",
        "name": "product",
        "display-name": "Product",
        "type": "dimension",
        "widget-type": "string/=",
        "dimension": ["field", 105, None],
        "default": ["2% Milk"],
    },
}

# 10 cards in layout order
CARD_DEFS = [
    {
        "name": "Total Products",
        "sql": "SELECT COUNT(*) AS total_products FROM analytics_analytics.dim_synthetic_products",
        "display": "scalar",
        "viz": {"scalar.field": "TOTAL_PRODUCTS"},
        "col": 0, "row": 0, "size_x": 4, "size_y": 3,
    },
    {
        "name": "Total Transactions",
        "sql": "SELECT SUM(units_sold)::bigint AS total_units_sold FROM analytics_analytics.fct_synthetic_daily_sales",
        "display": "scalar",
        "viz": {},
        "col": 4, "row": 0, "size_x": 4, "size_y": 3,
    },
    {
        "name": "Data Freshness",
        "sql": "SELECT MAX(transaction_date) AS last_update FROM analytics_analytics.fct_synthetic_daily_sales",
        "display": "scalar",
        "viz": {},
        "col": 8, "row": 0, "size_x": 4, "size_y": 3,
    },
    {
        "name": "Sales by Category",
        "sql": """SELECT category,
                  SUM(gross_sales)::numeric(12,2) AS total_sales,
                  SUM(units_sold)::bigint AS total_units
           FROM analytics_analytics.fct_synthetic_daily_sales
           GROUP BY category
           ORDER BY total_sales DESC""",
        "display": "bar",
        "viz": {
            "graph.dimensions": ["CATEGORY"],
            "graph.metrics": ["TOTAL_SALES"],
            "graph.x_axis.title_text": "Category",
            "graph.y_axis.title_text": "Total Sales ($)",
        },
        "col": 0, "row": 3, "size_x": 9, "size_y": 6,
    },
    {
        "name": "True vs Estimated Elasticity",
        "sql": """SELECT p.product_name, p.category, p.true_elasticity,
                  regr_slope(ln(s.units_sold::float), ln(s.price::float)) AS estimated_elasticity
           FROM analytics_analytics.fct_synthetic_daily_sales s
           JOIN analytics_analytics.dim_synthetic_products p ON s.upc = p.upc
           WHERE s.price > 0 AND s.units_sold > 0
           GROUP BY p.upc, p.product_name, p.category, p.true_elasticity""",
        "display": "scatter",
        "viz": {
            "graph.dimensions": ["TRUE_ELASTICITY"],
            "graph.metrics": ["ESTIMATED_ELASTICITY"],
            "graph.x_axis.title_text": "True Elasticity",
            "graph.y_axis.title_text": "Estimated Elasticity",
            "graph.label": "PRODUCT_NAME",
        },
        "col": 9, "row": 3, "size_x": 9, "size_y": 6,
    },
    {
        "name": "Daily Sales Trend",
        "sql": """SELECT transaction_date,
                  SUM(gross_sales)::numeric(12,2) AS daily_sales
           FROM analytics_analytics.fct_synthetic_daily_sales
           GROUP BY transaction_date
           ORDER BY transaction_date""",
        "display": "line",
        "viz": {
            "graph.dimensions": ["TRANSACTION_DATE"],
            "graph.metrics": ["DAILY_SALES"],
            "graph.x_axis.title_text": "Date",
            "graph.y_axis.title_text": "Daily Sales ($)",
        },
        "col": 0, "row": 9, "size_x": 14, "size_y": 6,
    },
    {
        "name": "Avg Validation Error %",
        "sql": """WITH product_elasticity AS (
               SELECT p.upc,
                      p.true_elasticity,
                      regr_slope(ln(s.units_sold::float), ln(s.price::float)) AS estimated
               FROM analytics_analytics.fct_synthetic_daily_sales s
               JOIN analytics_analytics.dim_synthetic_products p ON s.upc = p.upc
               WHERE s.units_sold > 0 AND s.price > 0
               GROUP BY p.upc, p.true_elasticity
           )
           SELECT ROUND(AVG(ABS(estimated - true_elasticity) / ABS(true_elasticity) * 100)::numeric, 2)
                  AS avg_error_pct
           FROM product_elasticity
           WHERE estimated IS NOT NULL""",
        "display": "scalar",
        "viz": {"scalar.suffix": "%"},
        "col": 14, "row": 9, "size_x": 4, "size_y": 6,
    },
    {
        "name": "Demand Curves: Price vs Quantity",
        "sql": DEMAND_CURVE_SQL,
        "display": "line",
        "viz": {
            "graph.dimensions": ["AVG_PRICE"],
            "graph.metrics": ["AVG_QUANTITY"],
            "graph.series_order_dimension": "PRODUCT",
            "graph.x_axis.title_text": "Price ($)",
            "graph.y_axis.title_text": "Avg Quantity Demanded",
        },
        "col": 0, "row": 15, "size_x": 9, "size_y": 8,
    },
    {
        "name": "Demand Curves: Log-Log (Slope = Elasticity)",
        "sql": LOG_DEMAND_SQL,
        "display": "line",
        "viz": {
            "graph.dimensions": ["LN_PRICE"],
            "graph.metrics": ["LN_QUANTITY"],
            "graph.series_order_dimension": "PRODUCT",
            "graph.x_axis.title_text": "ln(Price)",
            "graph.y_axis.title_text": "ln(Quantity)",
        },
        "col": 9, "row": 15, "size_x": 9, "size_y": 8,
    },
    {
        "name": "Demand Curve (Interactive)",
        "sql": INTERACTIVE_DEMAND_SQL,
        "display": "line",
        "viz": {
            "graph.dimensions": ["price", "product"],
            "graph.metrics": ["quantity"],
            "graph.x_axis.title_text": "Price ($)",
            "graph.y_axis.title_text": "Quantity Demanded",
            "graph.x_axis.scale": "linear",
            "graph.y_axis.auto_split": False,
        },
        "template_tags": INTERACTIVE_TEMPLATE_TAGS,
        "col": 0, "row": 23, "size_x": 18, "size_y": 8,
    },
]


def main():
    parser = argparse.ArgumentParser(description="Set up Metabase Grocery Analytics dashboard")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview creates/updates without writing anything")
    args = parser.parse_args()

    global DRY_RUN
    DRY_RUN = args.dry_run

    if DRY_RUN:
        print("=== DRY RUN (no changes will be made) ===\n")

    print("Connecting to Metabase API...")
    session = get_session()
    db_id = find_database(session)
    print(f"Found database id={db_id}\n")

    # ── Upsert 10 cards ──
    print("Cards:")
    card_ids = []
    for defn in CARD_DEFS:
        card_id = upsert_native_card(
            session, defn["name"], db_id,
            defn["sql"], defn["display"], defn["viz"],
            template_tags=defn.get("template_tags"),
        )
        card_ids.append(card_id)

    # ── Upsert dashboard ──
    print("\nDashboard:")
    dash_id = upsert_dashboard(
        session,
        "Grocery Analytics Overview",
        "Live analytics dashboard for the grocery analytics platform",
    )

    # ── Assign cards to dashboard layout ──
    if not DRY_RUN and dash_id > 0:
        # Fetch current dashcards to preserve their IDs (avoids re-creating dashcard rows)
        current = api(session, "get", f"/api/dashboard/{dash_id}")
        existing_dashcards = {dc["card_id"]: dc["id"] for dc in current.get("dashcards", [])}

        ordered_cards = []
        for i, (defn, card_id) in enumerate(zip(CARD_DEFS, card_ids), start=1):
            dashcard_id = existing_dashcards.get(card_id, -i)
            ordered_cards.append({
                "id": dashcard_id,
                "card_id": card_id,
                "col": defn["col"],
                "row": defn["row"],
                "size_x": defn["size_x"],
                "size_y": defn["size_y"],
            })

        api(session, "put", f"/api/dashboard/{dash_id}", json={
            "dashcards": ordered_cards,
        })
        print(f"  Layout updated with {len(ordered_cards)} cards")

    # ── Summary ──
    created = sum(1 for _ in [])  # counted via print statements above
    print(f"\nDashboard URL: {MB_URL}/dashboard/{dash_id}")
    print(f"Total cards managed: {len(CARD_DEFS)}"
          " (3 KPIs + category bar + elasticity scatter"
          " + daily trend + error % + 3 demand curves)")


if __name__ == "__main__":
    main()
