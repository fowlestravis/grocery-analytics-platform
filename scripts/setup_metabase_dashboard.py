"""
Set up Metabase dashboard for Grocery Analytics via the Metabase API.

Creates a dashboard with 7 card types:
  1. KPI cards (total products, total transactions, data freshness)
  2. Category performance (bar chart)
  3. Elasticity scatter plot (true vs estimated)
  4. Daily sales trend (line chart)
  5. Validation error % (big number)
  6. Demand curves (price vs quantity, line chart)
  7. Demand curves log-log (ln(price) vs ln(quantity), slope = elasticity)
"""

import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv()

MB_URL = os.environ.get("METABASE_URL", "http://localhost:3000")
MB_EMAIL = os.environ.get("METABASE_EMAIL")
MB_PASS = os.environ.get("METABASE_PASSWORD")


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


def create_native_card(session, name, db_id, sql, display="scalar", viz_settings=None):
    """Create a saved question using a native SQL query."""
    card = api(session, "post", "/api/card", json={
        "name": name,
        "dataset_query": {
            "type": "native",
            "native": {"query": sql},
            "database": db_id,
        },
        "display": display,
        "visualization_settings": viz_settings or {},
    })
    return card["id"]


def main():
    print("Connecting to Metabase API...")
    session = get_session()
    db_id = find_database(session)
    print(f"Found database id={db_id}")

    # -- Card 1: Total Products (KPI) --
    print("Creating card: Total Products...")
    c_products = create_native_card(session, "Total Products", db_id,
        "SELECT COUNT(*) AS total_products FROM analytics_analytics.dim_synthetic_products",
        display="scalar",
        viz_settings={"scalar.field": "TOTAL_PRODUCTS"})

    # -- Card 2: Total Transactions (KPI) --
    print("Creating card: Total Transactions...")
    c_transactions = create_native_card(session, "Total Transactions", db_id,
        "SELECT SUM(units_sold)::bigint AS total_units_sold FROM analytics_analytics.fct_synthetic_daily_sales",
        display="scalar")

    # -- Card 3: Data Freshness (KPI) --
    print("Creating card: Data Freshness...")
    c_freshness = create_native_card(session, "Data Freshness", db_id,
        "SELECT MAX(transaction_date) AS last_update FROM analytics_analytics.fct_synthetic_daily_sales",
        display="scalar")

    # -- Card 4: Category Performance (bar chart) --
    print("Creating card: Category Performance...")
    c_category = create_native_card(session, "Sales by Category", db_id,
        """SELECT category,
                  SUM(gross_sales)::numeric(12,2) AS total_sales,
                  SUM(units_sold)::bigint AS total_units
           FROM analytics_analytics.fct_synthetic_daily_sales
           GROUP BY category
           ORDER BY total_sales DESC""",
        display="bar",
        viz_settings={
            "graph.dimensions": ["CATEGORY"],
            "graph.metrics": ["TOTAL_SALES"],
            "graph.x_axis.title_text": "Category",
            "graph.y_axis.title_text": "Total Sales ($)",
        })

    # -- Card 5: Elasticity Scatter Plot (true vs estimated) --
    print("Creating card: Elasticity Scatter Plot...")
    c_elasticity = create_native_card(session, "True vs Estimated Elasticity", db_id,
        """SELECT p.product_name, p.category, p.true_elasticity,
                  regr_slope(ln(s.units_sold::float), ln(s.price::float)) AS estimated_elasticity
           FROM analytics_analytics.fct_synthetic_daily_sales s
           JOIN analytics_analytics.dim_synthetic_products p ON s.upc = p.upc
           WHERE s.price > 0 AND s.units_sold > 0
           GROUP BY p.upc, p.product_name, p.category, p.true_elasticity""",
        display="scatter",
        viz_settings={
            "graph.dimensions": ["TRUE_ELASTICITY"],
            "graph.metrics": ["ESTIMATED_ELASTICITY"],
            "graph.x_axis.title_text": "True Elasticity",
            "graph.y_axis.title_text": "Estimated Elasticity",
            "graph.label": "PRODUCT_NAME",
        })

    # -- Card 6: Daily Sales Trend (line chart) --
    print("Creating card: Daily Sales Trend...")
    c_trend = create_native_card(session, "Daily Sales Trend", db_id,
        """SELECT transaction_date,
                  SUM(gross_sales)::numeric(12,2) AS daily_sales
           FROM analytics_analytics.fct_synthetic_daily_sales
           GROUP BY transaction_date
           ORDER BY transaction_date""",
        display="line",
        viz_settings={
            "graph.dimensions": ["TRANSACTION_DATE"],
            "graph.metrics": ["DAILY_SALES"],
            "graph.x_axis.title_text": "Date",
            "graph.y_axis.title_text": "Daily Sales ($)",
        })

    # -- Card 8: Demand Curves (line chart) --
    # The centerpiece visualization showing price-quantity relationship
    print("Creating card: Demand Curves...")
    demand_curve_sql = """
        WITH selected_products AS (
            -- 5 products spanning the elasticity spectrum across categories
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
    c_demand = create_native_card(session, "Demand Curves: Price vs Quantity", db_id,
        demand_curve_sql,
        display="line",
        viz_settings={
            "graph.dimensions": ["AVG_PRICE"],
            "graph.metrics": ["AVG_QUANTITY"],
            "graph.series_order_dimension": "PRODUCT",
            "graph.x_axis.title_text": "Price ($)",
            "graph.y_axis.title_text": "Avg Quantity Demanded",
        })

    # -- Card 9: Demand Curves Log-Log (line chart) --
    print("Creating card: Demand Curves (Log-Log)...")
    log_demand_sql = demand_curve_sql.replace(
        "ROUND(AVG(price)::numeric, 2) AS avg_price",
        "ROUND(LN(AVG(price))::numeric, 3) AS ln_price"
    ).replace(
        "ROUND(AVG(units_sold)::numeric, 1) AS avg_quantity",
        "ROUND(LN(AVG(units_sold))::numeric, 3) AS ln_quantity"
    ).replace(
        "ORDER BY product_name, avg_price",
        "ORDER BY product_name, ln_price"
    )
    c_log_demand = create_native_card(session, "Demand Curves: Log-Log (Slope = Elasticity)", db_id,
        log_demand_sql,
        display="line",
        viz_settings={
            "graph.dimensions": ["LN_PRICE"],
            "graph.metrics": ["LN_QUANTITY"],
            "graph.series_order_dimension": "PRODUCT",
            "graph.x_axis.title_text": "ln(Price)",
            "graph.y_axis.title_text": "ln(Quantity)",
        })

    # -- Card 7: Validation Error % (big number) --
    print("Creating card: Validation Error %...")
    c_error = create_native_card(session, "Avg Validation Error %", db_id,
        """WITH product_elasticity AS (
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
        display="scalar",
        viz_settings={
            "scalar.suffix": "%",
        })

    # -- Create Dashboard --
    print("Creating dashboard...")
    dashboard = api(session, "post", "/api/dashboard", json={
        "name": "Grocery Analytics Overview",
        "description": "Live analytics dashboard for the grocery analytics platform",
    })
    dash_id = dashboard["id"]
    print(f"Dashboard created: id={dash_id}")

    # -- Add cards to dashboard with layout --
    cards = [
        # Row 1: KPI cards (3 across the top)
        {"id": c_products,     "col": 0,  "row": 0, "size_x": 4,  "size_y": 3},
        {"id": c_transactions, "col": 4,  "row": 0, "size_x": 4,  "size_y": 3},
        {"id": c_freshness,    "col": 8,  "row": 0, "size_x": 4,  "size_y": 3},
        # Row 2: Category bar chart + Elasticity scatter
        {"id": c_category,     "col": 0,  "row": 3, "size_x": 9,  "size_y": 6},
        {"id": c_elasticity,   "col": 9,  "row": 3, "size_x": 9,  "size_y": 6},
        # Row 3: Daily trend + Validation error
        {"id": c_trend,        "col": 0,  "row": 9, "size_x": 14, "size_y": 6},
        {"id": c_error,        "col": 14, "row": 9, "size_x": 4,  "size_y": 6},
        # Row 4: Demand curves (centerpiece)
        {"id": c_demand,       "col": 0,  "row": 15, "size_x": 9,  "size_y": 8},
        {"id": c_log_demand,   "col": 9,  "row": 15, "size_x": 9,  "size_y": 8},
    ]

    ordered_cards = []
    for i, card in enumerate(cards, start=1):
        ordered_cards.append({
            "id": -i,
            "card_id": card["id"],
            "col": card["col"],
            "row": card["row"],
            "size_x": card["size_x"],
            "size_y": card["size_y"],
        })

    api(session, "put", f"/api/dashboard/{dash_id}", json={
        "dashcards": ordered_cards,
    })

    print(f"\nDashboard ready at: {MB_URL}/dashboard/{dash_id}")
    print("Cards created: 9 (3 KPIs + category bar + elasticity scatter + daily trend + error % + 2 demand curves)")


if __name__ == "__main__":
    main()
