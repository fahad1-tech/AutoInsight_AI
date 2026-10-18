import numpy as np
import pandas as pd

from autoinsight.data_loader import classify_columns, load_csv, profile_dataset


def test_classify_columns_roles():
    n = 200
    df = pd.DataFrame({
        "row": np.arange(1, n + 1),                                   # running index
        "customer_id": np.arange(1000, 1000 + n),                     # id-like name
        "name": [f"person_{i}" for i in range(n)],                    # near-unique text
        "flag": np.tile([0, 1], n // 2),                              # 0/1 flag
        "amount": np.random.default_rng(0).normal(100, 10, n),        # measurement
        "city": np.tile(["A", "B", "C", "D"], n // 4),                # low-cardinality text
        "signup": pd.date_range("2024-01-01", periods=n, freq="D").astype(str),
    })
    roles = classify_columns(df)
    assert {"row", "customer_id", "name"} <= set(roles["identifier"])
    assert {"flag", "city"} <= set(roles["categorical"])
    assert roles["numeric"] == ["amount"]
    assert roles["datetime"] == ["signup"]


def test_names_containing_id_are_not_ids():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"width": rng.normal(10, 2, 300), "paid": rng.normal(50, 5, 300)})
    assert set(classify_columns(df)["numeric"]) == {"width", "paid"}


def test_profile_dataset_counts_duplicates_and_missing():
    df = pd.DataFrame({"a": [1, 1, 2, None], "b": ["x", "x", "y", "z"]})
    prof = profile_dataset(df)
    assert prof["n_rows"] == 4 and prof["n_cols"] == 2
    assert prof["duplicate_rows"] == 1
    assert prof["missing_total_pct"] > 0


def test_load_csv_strips_column_whitespace(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text(" a , b \n1,2\n")
    assert list(load_csv(str(path)).columns) == ["a", "b"]
