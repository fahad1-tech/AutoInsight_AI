import numpy as np

from autoinsight import churn, data_loader, kpis


def _columns(df, target=None):
    cols = data_loader.classify_columns(df)
    if target:
        for key in ("numeric", "categorical", "identifier"):
            cols[key] = [c for c in cols[key] if c != target]
    return cols


def test_churn_kpis_are_built_from_the_data(churn_df):
    cols = _columns(churn_df, "Churn")
    res = churn.analyze_churn(churn_df, "Churn", cols["categorical"], cols["numeric"])
    kpi_list, focus = kpis.churn_kpis(res, cols)
    labels = [k["label"] for k in kpi_list]
    assert labels[0] == "Churn rate"
    assert any("Balance" in label for label in labels)           # money column detected
    badged = [k for k in kpi_list if k.get("badge") == "Most useful"]
    assert len(badged) == 1 and focus["label"] == badged[0]["label"]
    assert "Contract" in focus["label"]


def test_generic_kpis_use_money_columns(retail_df):
    cols = _columns(retail_df)
    kpi_list, focus = kpis.generic_kpis(retail_df, cols, trends={})
    labels = [k["label"] for k in kpi_list]
    assert "Total revenue" in labels and not any("Churn" in label for label in labels)
    assert focus is not None


def test_kpis_differ_between_datasets(churn_df, retail_df):
    c = _columns(churn_df, "Churn")
    res = churn.analyze_churn(churn_df, "Churn", c["categorical"], c["numeric"])
    churn_labels = {k["label"] for k in kpis.churn_kpis(res, c)[0]}
    retail_labels = {k["label"] for k in kpis.generic_kpis(retail_df, _columns(retail_df), {})[0]}
    assert churn_labels.isdisjoint(retail_labels)


def test_fmt_compacts_large_numbers():
    assert kpis.fmt(1_500_000) == "1.50M"
    assert kpis.fmt(12_345) == "12.3K"
    assert kpis.fmt(42) == "42"


def test_prices_are_averaged_not_summed(retail_df):
    retail_df["unit_price"] = np.linspace(5, 15, len(retail_df))
    kpi_list, _ = kpis.generic_kpis(retail_df, _columns(retail_df), trends={})
    labels = [k["label"] for k in kpi_list]
    assert "Average unit_price" in labels and "Total unit_price" not in labels
