# Grocery Analytics Platform

A grocery pricing analytics platform that estimates price elasticity of demand using log-log regression, validates the methodology against actual sales data, and surfaces actionable pricing recommendations through an interactive demand curve tool.

📊 **[View the Tableau Public Dashboard](https://public.tableau.com/app/profile/tvfowles/viz/Elasticityv1/Dashboard1)**

---

## Part 1 — The Pricing Tool

### Background

This dashboard is meant as a unit pricing guidance tool for assortment and promotional decisions made by retail category managers. It was inspired by and built using methodology from my time at Whole Foods Market. This implementation keeps the core analytical approach, while the synthetic grocery data source is built using a modern open-source stack, and the outputs are published to Tableau Public.

### The Business Problem

Retailers — and grocers especially — need to understand how changing an item's price will affect its demand. This is a fundamental concept in microeconomics. To use an example from this dataset: a 10% price increase on milk will not cause many customers to go without, because milk has inelastic demand. However, a 10% increase on Potato Chips could cut sales significantly due to their elastic demand — customers will either trade down to a lower tier brand or skip the chips entirely.

Quantifying these changes — what microeconomists call the price elasticity of demand — is an important part of pricing analysis, promotion planning, and category management. This project is meant to solve a common problem with retail data: gaps or lack of clean sales data. Each product in this synthetic dataset has a known elasticity assigned from category-appropriate ranges found in academic economics literature (generally speaking, dairy staples are relatively inelastic, snacks relatively elastic, etc.). Those known elasticities are baked into the synthetic transaction data, and the regression methodology is then tested to see whether it can recover them. If the methodology we use can recover elasticities we already know to be true, we can trust it on real transactional data where the true elasticity is unknown.

**Key result:** The pipeline validates log-log regression methodology for production use with a **2.4% average elasticity error** across 32 products.

### Demand Curve Methodology

The demand curve is constructed from log-log regression coefficients using the exponential form of the constant-elasticity model. We use logs and exponents in the equation to smooth the underlying data and control for outliers:

```
Q(P) = b_intercept_exp × e^(b_ARP × P)
```

At any given price point the model predicts three curves:

- **Units** — volume response to price change
- **Sales** — revenue (units × price)
- **Contribution Margin** — direct product margin: `Contribution Margin = Sales − (Units × Cost)`

> **Note:** This is not a true contribution margin in the accounting sense, as it does not account for variable costs like labor, packaging, shrink, and theft. However, it makes sense as a target KPI for category managers and merchandising leadership, as finance typically sets margin targets at the category level against this metric.

In the real world, elasticity isn't perfectly constant across all prices. Diminishing marginal utility means the eighth unit of a product is worth less to a consumer than the first, so price sensitivity can shift as price deviates further from where customers are expecting it. The constant-elasticity assumption is a useful approximation for the price ranges typically seen in grocery retail, where prices typically move incrementally rather than dramatically.

### The Balance Point

The **balance point** is the price within the observed range that maximizes contribution margin. It is identified by evaluating the demand curve across the full observed price range in $0.01 increments and finding the peak of the margin curve.

The **margin opportunity** quantifies the margin being left on the table at the current retail price:

```
Margin Opportunity = Margin(balance_point_price) − Margin(current_price)
```

Expressed in average dollars per store per day, this metric is immediately actionable. A margin opportunity of $100/store/day across 300 stores represents $30,000/day in unrealized contribution margin.

### The Dashboard

The Tableau Public dashboard provides an interactive product-level pricing tool across 32 grocery products spanning four categories — Dairy, Produce, Snacks, and Beverages.

- **Product selector** — choose any product from a dropdown filter and all views will update dynamically
- **Three-curve demand visualization** — Units, Sales, and Contribution Margin plotted across the full observed price range with the balance point annotated
- **Historical metrics panel** — current observed sales, contribution margin, units, and average retail price across all stores' observed sales
- **Balance point panel** — revenue at optimal price, maximum achievable contribution margin, margin opportunity, and the optimal price itself

### A Note on Tableau Public vs Metabase

The data pipeline runs a live Metabase instance connected directly to a PostgreSQL instance on a dedicated Mac Mini I use as a server. For ease of sharing externally, I elected to publish the pricing tool to Tableau Public instead. This is the right choice for sharing externally as no authentication is needed, and all the data can be accessed from a single URL. The tradeoff is that Tableau Public only supports static data, so the dashboard is built from CSV exports rather than a live connection. In production this would run on Tableau Server with data sources pointing at live data mart tables on a scheduled refresh.

### Model Limitations

The elasticity estimation methodology (log-log regression: `ln(Q) = β₀ + β₁ × ln(P)`) was validated at 2.4% average error across 32 products, with β₁ representing a constant elasticity — the percentage change in quantity demanded for a 1% change in price. The ~2.4% estimation error from Method 2 (within-product time series) never changes the recommended pricing direction for any product.

**Demand curve form.** The current dashboard generates demand curves using a log-linear (exponential) form (`Q(P) = a × e^(ε × P)`), where the point elasticity varies with price rather than staying constant. A three-way comparison against the correct constant-elasticity power form (`Q(P) = A × P^ε`) shows that this choice flips the recommended pricing direction (raise vs. lower) for 26 of 32 products. The exponential form systematically biases balance points downward because it overweights price sensitivity at higher prices. The dashboard curves are being rebuilt with the power form, which is the direct solution to the log-log model and maintains constant elasticity across the curve.

**Edge optimums.** Under the power form, all 32 products' balance points fall at the maximum of the observed price range. For inelastic products (|ε| < 1), this is economically expected — margin always increases with price when demand drops less than proportionally. For elastic products, it indicates the observed price range is too narrow for the margin curve to peak within it. Practitioners should treat the balance point as a directional indicator rather than a precise target, and incorporate competitive pricing floors and category strategy before acting on the recommendation.

**Demand curve inputs.** The demand curve generation currently uses the known true elasticity values from the synthetic data, not the regression estimates from Method 2. Since the estimation error is small (~2.4%) and never changes the pricing direction, this does not affect the qualitative conclusions, but a production implementation would use the estimated values.

---

## Part 2 — The Data Engineering Stack

*Coming soon.* This section will cover the synthetic data generation approach, the five-layer dbt pipeline, validation methodology, Airflow orchestration, and infrastructure decisions. The short version: a PostgreSQL warehouse running in Docker, transformed by dbt, orchestrated by Airflow, and validated against known ground truth with ~2.4% average elasticity error across 32 products.

---

## Getting Started

```bash
cp .env.example .env   # then fill in your database and Metabase credentials
docker compose up -d    # starts PostgreSQL warehouse + Metabase
```

Docker Compose requires `.env` to be present — it will error on missing password variables. See `.env.example` for the full list.

## Known Limitations

- Three products exceed 5% estimation error: **Bell Peppers** (6.2%, Produce), **Cheddar Cheese** (5.7%, Dairy), and **Greek Yogurt** (5.2%, Dairy). All have low-magnitude elasticities (|ε| < 1.3) where small absolute errors produce larger percentage errors.

## Key Dependencies

`dbt-postgres` · `pandas` · `numpy` · `scipy` · `matplotlib` · `seaborn` · `sqlalchemy` · `psycopg2-binary` · `faker` · `python-dotenv`