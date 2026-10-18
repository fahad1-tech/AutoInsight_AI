import pandas as pd

from autoinsight import data_loader
from autoinsight.churn import analyze_churn, churn_insights, detect_target, to_binary


def test_to_binary_handles_common_encodings():
    r = to_binary(pd.Series(["Yes", "no", "YES", None]))
    assert r.iloc[:3].tolist() == [1.0, 0.0, 1.0] and pd.isna(r.iloc[3])
    assert to_binary(pd.Series([1, 0, 1.0])).tolist() == [1.0, 0.0, 1.0]
    assert to_binary(pd.Series([True, False])).tolist() == [1.0, 0.0]
    assert to_binary(pd.Series([0, 1, 2])).isna().all()          # not binary


def test_detect_target(churn_df):
    assert detect_target(churn_df) == "Churn"
    assert detect_target(churn_df.drop(columns="Churn")) is None
    assert detect_target(pd.DataFrame({"left_date": ["2024-01-01", "2024-02-01"]})) is None


def test_strongest_driver_is_ranked_first(churn_df):
    res = analyze_churn(churn_df, "Churn", ["Contract", "Region"], ["Support Calls", "Balance"])
    assert 0 < res["overall_rate"] < 1
    assert res["ranked"][0][0] == "Contract"
    assert res["importance"][0][2] == 100.0                      # relative importance is scaled to 100
    strengths = [i["strength"] for _, i in res["ranked"]]
    assert strengths == sorted(strengths, reverse=True)


def test_churn_insights_start_with_overall_rate(churn_df):
    cols = data_loader.classify_columns(churn_df)
    res = analyze_churn(churn_df, "Churn", cols["categorical"], [c for c in cols["numeric"] if c != "Churn"])
    insights = churn_insights(res)
    assert insights[0].title == "Overall Churn Rate"
    assert any("Contract" in i.title for i in insights)
