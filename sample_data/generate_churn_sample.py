"""Creates two churn CSVs (train + test) with the same columns, to demo churn mode."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)


def make(n, start_id):
    age = rng.integers(18, 70, n)
    gender = rng.choice(["Male", "Female"], n)
    tenure = rng.integers(1, 60, n)
    usage = rng.integers(1, 30, n)
    support_calls = rng.poisson(3, n)
    payment_delay = rng.integers(0, 30, n)
    sub = rng.choice(["Basic", "Standard", "Premium"], n, p=[0.35, 0.4, 0.25])
    contract = rng.choice(["Monthly", "Quarterly", "Annual"], n, p=[0.45, 0.3, 0.25])
    spend = rng.normal(600, 200, n).clip(50)
    logit = (-2.0 + 0.30 * support_calls + 0.05 * payment_delay - 0.025 * tenure
             + np.select([contract == "Monthly", contract == "Quarterly"], [1.0, 0.3], -1.0)
             + 0.4 * (gender == "Male") + 0.5 * (age > 50))
    churn = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return pd.DataFrame({
        "CustomerID": np.arange(start_id, start_id + n), "Age": age, "Gender": gender,
        "Tenure": tenure, "Usage Frequency": usage, "Support Calls": support_calls,
        "Payment Delay": payment_delay, "Subscription Type": sub,
        "Contract Length": contract, "Total Spend": spend.round(2), "Churn": churn})


make(3000, 1).to_csv("sample_data/churn_train.csv", index=False)
make(1000, 3001).to_csv("sample_data/churn_test.csv", index=False)
print("Created sample_data/churn_train.csv and sample_data/churn_test.csv")
