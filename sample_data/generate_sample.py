"""
Generates a synthetic retail sales dataset (with intentional data-quality
issues, trends, and correlations) purely to demo AutoInsight AI end-to-end.
Not required for real usage -- point main.py at your own CSV instead.
"""
import numpy as np
import pandas as pd

np.random.seed(42)
n = 2000

regions = np.random.choice(
    ["North", "South", "East", "West", "Central"], n, p=[0.35, 0.25, 0.15, 0.15, 0.10]
)
channels = np.random.choice(["Online", "Retail Store", "Partner"], n, p=[0.55, 0.35, 0.10])
categories = np.random.choice(
    ["Electronics", "Apparel", "Home Goods", "Beauty", "Sports"], n
)

dates = pd.date_range("2023-01-01", periods=18, freq="ME")
date_col = np.random.choice(dates, n)

base_price = np.random.gamma(shape=3, scale=40, size=n)
# North region intentionally outperforms -> creates a "performance gap" insight
region_boost = pd.Series(regions).map(
    {"North": 1.4, "South": 1.0, "East": 0.8, "West": 0.9, "Central": 0.6}
).values
units = np.random.poisson(3, n) + 1
revenue = base_price * units * region_boost

# Inject a declining trend in the last few months for "Home Goods"
month_idx = pd.Series(date_col).rank(method="dense").astype(int).values
decline_mask = categories == "Home Goods"
revenue = np.where(decline_mask, revenue * (1 - 0.03 * month_idx), revenue)

# Marketing spend correlated with revenue (for correlation insight)
marketing_spend = revenue * np.random.uniform(0.08, 0.15, n) + np.random.normal(0, 5, n)
marketing_spend = np.clip(marketing_spend, 0, None)

customer_satisfaction = np.clip(
    np.random.normal(4.2, 0.6, n) - (marketing_spend < 5) * 0.5, 1, 5
)

df = pd.DataFrame({
    "order_id": [f"ORD{10000+i}" for i in range(n)],
    "order_date": date_col,
    "region": regions,
    "sales_channel": channels,
    "product_category": categories,
    "units_sold": units,
    "unit_price": base_price.round(2),
    "revenue": revenue.round(2),
    "marketing_spend": marketing_spend.round(2),
    "customer_satisfaction": customer_satisfaction.round(1),
})

# Inject missing values
for col in ["customer_satisfaction", "marketing_spend"]:
    idx = np.random.choice(df.index, size=int(n * 0.05), replace=False)
    df.loc[idx, col] = np.nan

# Inject duplicates
df = pd.concat([df, df.sample(30, random_state=1)], ignore_index=True)

# Inject a few extreme outliers
outlier_idx = np.random.choice(df.index, size=5, replace=False)
df.loc[outlier_idx, "revenue"] *= 15

df.to_csv("sample_data/retail_sales_sample.csv", index=False)
print(f"Generated sample_data/retail_sales_sample.csv with {len(df)} rows")
