import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def churn_df() -> pd.DataFrame:
    """Synthetic churn data where `Contract` is by far the strongest driver."""
    rng = np.random.default_rng(0)
    n = 1500
    contract = rng.choice(["Monthly", "Annual"], n, p=[0.5, 0.5])
    region = rng.choice(["North", "South", "East"], n)            # pure noise
    calls = rng.poisson(3, n)
    balance = rng.normal(5000, 1500, n).clip(0)
    logit = -2.0 + 3.0 * (contract == "Monthly") + 0.05 * calls
    churn = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return pd.DataFrame({
        "CustomerID": np.arange(1, n + 1), "Contract": contract, "Region": region,
        "Support Calls": calls, "Balance": balance.round(2), "Churn": churn})


@pytest.fixture
def retail_df() -> pd.DataFrame:
    """Non-churn data: revenue by region over time."""
    rng = np.random.default_rng(1)
    n = 600
    return pd.DataFrame({
        "order_date": rng.choice(pd.date_range("2024-01-01", periods=12, freq="MS"), n),
        "region": rng.choice(["North", "South", "West"], n),
        "units": rng.integers(1, 9, n),
        "revenue": rng.gamma(3, 40, n).round(2)})
