import pytest

from autoinsight.cli import main
from autoinsight.pipeline import run_pipeline


def test_churn_dashboard_end_to_end(tmp_path, churn_df):
    csv = tmp_path / "customers.csv"
    churn_df.to_csv(csv, index=False)
    out = tmp_path / "report.html"
    run_pipeline([str(csv)], str(out))
    html = out.read_text(encoding="utf-8")
    assert "Key Performance Indicators" in html
    assert "Churn Drivers" in html and "Most useful" in html
    assert "<script>" in html and "showPage" in html              # navigation is wired up


def test_non_churn_dataset_gets_different_dashboard(tmp_path, retail_df):
    csv = tmp_path / "sales.csv"
    retail_df.to_csv(csv, index=False)
    out = tmp_path / "report.html"
    run_pipeline([str(csv)], str(out))
    html = out.read_text(encoding="utf-8")
    assert "Total revenue" in html
    assert 'data-page="Churn Drivers"' not in html


def test_two_files_with_same_columns_are_combined(tmp_path, churn_df):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    churn_df.iloc[:700].to_csv(a, index=False)
    churn_df.iloc[700:].to_csv(b, index=False)
    out = tmp_path / "report.html"
    assert main([str(a), str(b), "-o", str(out)]) == 0
    assert "1,500 rows" in out.read_text(encoding="utf-8")


def test_files_with_different_columns_are_rejected(tmp_path, churn_df, retail_df):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    churn_df.to_csv(a, index=False)
    retail_df.to_csv(b, index=False)
    with pytest.raises(SystemExit):
        run_pipeline([str(a), str(b)], str(tmp_path / "r.html"))


def test_unknown_target_column_is_rejected(tmp_path, churn_df):
    csv = tmp_path / "c.csv"
    churn_df.to_csv(csv, index=False)
    with pytest.raises(SystemExit):
        run_pipeline([str(csv)], str(tmp_path / "r.html"), target="NoSuchColumn")
