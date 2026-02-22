"""
Set up Metabase dashboard for Grocery Analytics via the Metabase API.

Creates a dashboard with 5 card types:
  1. KPI cards (total products, total transactions, data freshness)
  2. Category performance (bar chart)
  3. Elasticity scatter plot (true vs estimated)
  4. Daily sales trend (line chart)
  5. Validation error % (big number)
"""

import requests
import sys

MB_URL = "http://localhost:3000"
MB_EMAIL = "tvfowles@gmail.com"
MB_PASS = "MzJVDGqvPQyNRpEW1CJ#"


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
        # TODO(human): Write the SQL query for the elasticity scatter plot
        """SELECT PRODUCT_NAME,
		CATEGORY,
		TRUE_ELASTICITY,
		ESTIMATED_ELASTICITY
		FROM analytics_analytics.fct_synthetic_daily_sales
		JOIN analytics_analytics.dim_synthetic_products using (upc)
	""",
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
    ]

    ordered_cards = []
    for card in cards:
        ordered_cards.append({
            "id": -1,
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
    print("Cards created: 7 (3 KPIs + category bar + elasticity scatter + daily trend + error %)")


if __name__ == "__main__":
    main()
