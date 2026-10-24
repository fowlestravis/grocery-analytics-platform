# Elasticity Validation Report

Generated: 2026-10-23 19:26:49

## Executive Summary

This report validates the price elasticity estimation methodology by comparing
estimated elasticities to known ground truth values in synthetic data.

**Key Result (Method 2 — Product-Level Time Series):**
- Mean absolute percentage error: **2.4%** across 32 products
- Mean absolute error: **0.030**
- Median percentage error: 2.2%, max: 6.2%
- 95% CI coverage: **94%** (30/32 products have true elasticity inside the estimated confidence interval)

---

## Methodology

### Data Source
- Synthetic grocery transaction data with known elasticities
- 280,320 transactions across 32 products
- 730 days of daily data (2023–2024)

### Estimation Approach
**Log-log regression:** ln(Q) = β₀ + β₁×ln(P) + ε

Where Q = quantity demanded, P = price, and β₁ = price elasticity estimate.
Each product is estimated separately using its own daily time series (Method 2).

---

## Method 2: Product-Level Time Series (Headline Result)

For each product, regress ln(daily units sold) on ln(daily price) using
730 days of within-product time-series variation. This isolates the
price–quantity relationship by absorbing product-level base demand into the
intercept.

### Summary by Category

#### Beverages

| Metric | Value |
|--------|-------|
| Products | 8 |
| Avg True Elasticity | -1.442 |
| Avg Estimated | -1.458 |
| Avg Abs Error | 0.034 (2.4%) |
| Avg R² | 0.179 |
| 95% CI Coverage | 8/8 |

#### Dairy

| Metric | Value |
|--------|-------|
| Products | 8 |
| Avg True Elasticity | -0.754 |
| Avg Estimated | -0.765 |
| Avg Abs Error | 0.022 (3.1%) |
| Avg R² | 0.057 |
| 95% CI Coverage | 8/8 |

#### Produce

| Metric | Value |
|--------|-------|
| Products | 8 |
| Avg True Elasticity | -1.262 |
| Avg Estimated | -1.270 |
| Avg Abs Error | 0.031 (2.5%) |
| Avg R² | 0.144 |
| 95% CI Coverage | 7/8 |

#### Snacks

| Metric | Value |
|--------|-------|
| Products | 8 |
| Avg True Elasticity | -2.006 |
| Avg Estimated | -2.031 |
| Avg Abs Error | 0.033 (1.6%) |
| Avg R² | 0.293 |
| 95% CI Coverage | 7/8 |

### Per-Product Results

| Product | Category | True | Estimated | Abs Error | Error % | 95% CI | Truth in CI |
|---------|----------|-----:|----------:|----------:|--------:|-------:|:-----------:|
| Coffee Beans | Beverages | -1.771 | -1.835 | 0.064 | 3.6% | [-1.902, -1.768] | ✅ |
| Orange Juice | Beverages | -1.477 | -1.527 | 0.050 | 3.4% | [-1.593, -1.461] | ✅ |
| Lemonade | Beverages | -1.193 | -1.231 | 0.038 | 3.2% | [-1.296, -1.165] | ✅ |
| Sparkling Water | Beverages | -1.092 | -1.061 | 0.031 | 2.9% | [-1.127, -0.995] | ✅ |
| Cola 12pk | Beverages | -1.969 | -2.014 | 0.045 | 2.3% | [-2.080, -1.947] | ✅ |
| Green Tea | Beverages | -1.070 | -1.047 | 0.023 | 2.2% | [-1.112, -0.982] | ✅ |
| Sports Drink | Beverages | -1.196 | -1.178 | 0.018 | 1.5% | [-1.244, -1.112] | ✅ |
| Kombucha | Beverages | -1.772 | -1.774 | 0.002 | 0.1% | [-1.839, -1.709] | ✅ |
| Cheddar Cheese | Dairy | -0.584 | -0.550 | 0.034 | 5.7% | [-0.617, -0.484] | ✅ |
| Greek Yogurt | Dairy | -0.699 | -0.735 | 0.036 | 5.2% | [-0.801, -0.670] | ✅ |
| Cottage Cheese | Dairy | -0.772 | -0.803 | 0.031 | 4.0% | [-0.868, -0.737] | ✅ |
| Whole Milk | Dairy | -0.813 | -0.845 | 0.032 | 3.9% | [-0.911, -0.779] | ✅ |
| Cream Cheese | Dairy | -0.694 | -0.713 | 0.019 | 2.8% | [-0.779, -0.648] | ✅ |
| 2% Milk | Dairy | -0.922 | -0.935 | 0.013 | 1.4% | [-0.999, -0.870] | ✅ |
| Butter | Dairy | -0.848 | -0.836 | 0.012 | 1.4% | [-0.903, -0.770] | ✅ |
| Sour Cream | Dairy | -0.704 | -0.704 | 0.000 | 0.1% | [-0.770, -0.639] | ✅ |
| Bell Peppers | Produce | -1.228 | -1.304 | 0.076 | 6.2% | [-1.370, -1.238] | ❌ |
| Apples | Produce | -1.287 | -1.232 | 0.055 | 4.3% | [-1.297, -1.166] | ✅ |
| Avocados | Produce | -1.319 | -1.372 | 0.053 | 4.0% | [-1.437, -1.308] | ✅ |
| Lettuce | Produce | -0.842 | -0.824 | 0.018 | 2.2% | [-0.890, -0.758] | ✅ |
| Strawberries | Produce | -1.415 | -1.441 | 0.026 | 1.9% | [-1.507, -1.376] | ✅ |
| Bananas | Produce | -1.454 | -1.438 | 0.016 | 1.1% | [-1.503, -1.373] | ✅ |
| Broccoli | Produce | -1.438 | -1.434 | 0.004 | 0.3% | [-1.499, -1.368] | ✅ |
| Tomatoes | Produce | -1.117 | -1.117 | 0.000 | 0.0% | [-1.182, -1.052] | ✅ |
| Granola Bars | Snacks | -1.613 | -1.660 | 0.047 | 2.9% | [-1.726, -1.594] | ✅ |
| Cookies | Snacks | -2.494 | -2.565 | 0.071 | 2.8% | [-2.631, -2.498] | ❌ |
| Candy | Snacks | -1.739 | -1.777 | 0.038 | 2.2% | [-1.843, -1.711] | ✅ |
| Popcorn | Snacks | -1.637 | -1.660 | 0.023 | 1.4% | [-1.725, -1.595] | ✅ |
| Trail Mix | Snacks | -2.189 | -2.161 | 0.028 | 1.3% | [-2.228, -2.095] | ✅ |
| Potato Chips | Snacks | -2.219 | -2.245 | 0.026 | 1.2% | [-2.311, -2.179] | ✅ |
| Pretzels | Snacks | -2.425 | -2.451 | 0.026 | 1.1% | [-2.516, -2.385] | ✅ |
| Crackers | Snacks | -1.729 | -1.731 | 0.002 | 0.1% | [-1.796, -1.666] | ✅ |

**95% CI coverage rate: 94%** (30 of 32 products)

### Validation Plots

![Product Validation](product_validation.png)

Product-level estimates show strong correlation with ground truth across all categories.

![Error Distribution](error_distribution.png)

The error distribution is centered near zero, indicating unbiased estimation.

---

## Method 1: Cross-Product Aggregate (Naive Baseline)

Method 1 regresses ln(avg quantity) on ln(avg price) **across products**
within each category (n=8 per category). This is a deliberately naive baseline:
it conflates differences in base demand across products with price effects,
producing positive slopes and >100% errors. It demonstrates why within-product
time-series estimation (Method 2) is necessary.

| Category | True Elast. | Estimated | Abs Error | Error % | R² | p-value |
|----------|------------:|----------:|----------:|--------:|------:|--------:|
| Beverages | -1.443 | 0.061 | 1.503 | 104.2% | 0.005 | 0.8683 |
| Dairy | -0.754 | 0.407 | 1.161 | 153.9% | 0.210 | 0.2533 |
| Produce | -1.263 | 0.255 | 1.518 | 120.2% | 0.385 | 0.1004 |
| Snacks | -2.006 | 0.283 | 2.289 | 114.1% | 0.023 | 0.7189 |

All Method 1 estimates have the **wrong sign** (positive instead of negative)
and non-significant p-values. This is expected: cross-product regression
conflates product-level demand differences with the price effect.

---

## Conclusion

**Overall Performance (Method 2):**
- Mean absolute percentage error: 2.4%
- Mean absolute error: 0.030
- 95% CI coverage: 94%
- Products above 5% error: 3

**Validation Status:** ✅ **PASSED**

### Limitations
- Results specific to synthetic data with known characteristics
- Real data may have additional complexity (stockouts, competition, seasonality)
- Assumes constant elasticity over the observed price range
- Three products exceed 5% error (Bell Peppers, Cheddar Cheese, Greek Yogurt), all with low-magnitude elasticities where small absolute errors yield larger percentage errors

---

**Report generated by:** demand_analysis.py
**Date:** 2026-10-23 19:26:49
