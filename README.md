# Grocery Analytics Platform

A grocery pricing analytics platform that estimates price elasticity of demand using log-log regression, validates the methodology against known ground truth, and surfaces actionable pricing recommendations through an interactive demand curve tool. Built on a modern data engineering stack running 24/7 on a Mac Mini.

📊 **[View the Tableau Public Dashboard](https://public.tableau.com/app/profile/tvfowles/viz/Elasticityv1/Dashboard1)**

-----

## Part 1 — The Pricing Tool

### Background

This project reconstructs a pricing decision support tool for assortment and promotional decisions used by category managers. It was inspired by and built using methodology I was exposed to in a production pricing environment at Whole Foods Market. This implementation reproduces the core analytical approach on a modern open-source stack using synthetic grocery data, with outputs published via Tableau Public.

### The Business Problem

Retailers — and grocers especially — need to understand how changes in an item’s price will affect its demand. This is a fundamental concept in microeconomics. To use an example from this dataset: a 10% price increase on milk will not cause many customers to go without, because milk has inelastic demand. However, a 10% increase on Potato Chips could cut sales significantly due to their elastic demand — customers will either trade down or go without entirely.

Quantifying these changes — the price elasticity of demand — is a keystone of pricing analysis, promotion planning, and category management. This project is an MVP of a solution to a common problem in retail analytics: gaps in or unavailability of clean transactional data. By generating synthetic grocery transactions with known elasticities baked in and then verifying them using econometric methodology, we can demonstrate that if the approach works on synthetic data, it can be trusted on real transactional data as well.

**Key result:** The pipeline validates log-log regression methodology for production use with a **2.4% MAPE** across 32 products.

### Demand Curve Methodology

The demand curve is constructed from log-log regression coefficients using the exponential form of the constant-elasticity model:

```
Q(P) = b_intercept_exp × e^(b_ARP × P)
```

At any given price point the model predicts three curves:

- **Units** — volume response to price change
- **Sales** — revenue (units × price)
- **Contribution Margin** — direct product margin: `Contribution Margin = Sales − (Units × Cost)`

> **A note on margin terminology:** In the Whole Foods production environment this metric was referred to as GIG — Gross Income from Groceries. GIG captures per-unit profitability using direct product cost only, before allocating variable costs such as labor, packaging, and shrink. It is not a true contribution margin in the academic sense, but it is the preferred KPI for category managers and merchandising leadership, as finance typically sets margin targets at the category level against this metric. The terms are used interchangeably in this project.

### The Balance Point

The **balance point** is the price within the observed range that maximizes contribution margin. It is identified by evaluating the demand curve across the full observed price range in $0.01 increments and finding the peak of the margin curve.

The **margin opportunity** quantifies the margin being left on the table at the current retail price:

```
Margin Opportunity = Margin(balance_point_price) − Margin(current_price)
```

Expressed in dollars per store per day, this metric is immediately actionable. A margin opportunity of $100/store/day across 300 stores represents $30,000/day in unrealized contribution margin.

### The Dashboard

The Tableau Public dashboard provides an interactive product-level pricing tool across 32 synthetic grocery products spanning four categories — Dairy, Produce, Snacks, and Beverages.

- **Product selector** — choose any product from a dropdown; all views update dynamically
- **Three-curve demand visualization** — Units, Sales, and Contribution Margin plotted across the full observed price range with the balance point annotated
- **Historical metrics panel** — current observed sales, contribution margin, units, and average retail price across all stores’ observed sales
- **Balance point panel** — revenue at optimal price, maximum achievable contribution margin, margin opportunity, and the optimal price itself

### A Note on Tableau Public vs Metabase

The pipeline runs a live Metabase instance connected directly to PostgreSQL on the Mac Mini. For ease of sharing externally, I elected to publish the pricing tool to **Tableau Public** instead. Tableau Public makes the dashboard accessible via a single URL with no authentication required, which is the practical choice for a portfolio project.

The tradeoff is that Tableau Public only supports static data — the dashboard is built from CSV exports of the PostgreSQL data marts rather than a live database connection. In a production environment this tool would be published to **Tableau Server**, with data sources pointing at live mart tables that refresh on a scheduled cadence, eliminating the manual CSV export step entirely.

### Model Limitations

For highly elastic products (elasticity < -1.8), the contribution margin curve tends to peak at or near the minimum observed price. The log-linear model predicts that volume gains from price reduction continue to outweigh margin losses across the observed range, meaning the balance point recommendation for these products is effectively “price as low as you have historically tested.” This is consistent with economic theory but not always actionable in practice. Practitioners should treat the balance point as a directional indicator rather than a precise target for highly elastic SKUs, and incorporate competitive pricing floors and category strategy before acting on the recommendation.

-----

## Part 2 — The Data Engineering Stack

*Coming soon. This section will cover the synthetic data generation approach, the five-layer dbt pipeline, validation methodology, Airflow orchestration, and infrastructure decisions. The short version: a PostgreSQL warehouse running in Docker, transformed by dbt, orchestrated by Airflow, and validated against known ground truth with ~2.4% MAPE across 32 products.*

-----

## Key Dependencies

`dbt-postgres` · `pandas` · `numpy` · `scipy` · `matplotlib` · `seaborn` · `sqlalchemy` · `psycopg2-binary` · `faker` · `python-dotenv`
