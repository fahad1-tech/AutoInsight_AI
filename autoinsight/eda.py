"""
eda.py
------
Automated Exploratory Data Analysis. Produces the structured statistics that
insights.py reasons over and report.py renders. No hardcoded column names -
everything is derived from the column classification passed in.
"""

import pandas as pd
import numpy as np


def missing_value_report(df: pd.DataFrame) -> pd.DataFrame:
    missing = df.isna().sum()
    pct = (missing / len(df) * 100).round(2)
    out = pd.DataFrame({"missing_count": missing, "missing_pct": pct})
    return out[out["missing_count"] > 0].sort_values("missing_pct", ascending=False)


def numeric_summary(df: pd.DataFrame, numeric_cols: list) -> pd.DataFrame:
    if not numeric_cols:
        return pd.DataFrame()
    desc = df[numeric_cols].describe().T
    desc["skew"] = df[numeric_cols].skew()
    desc["missing_pct"] = (df[numeric_cols].isna().mean() * 100).round(2)
    return desc.round(2)


def categorical_summary(df: pd.DataFrame, categorical_cols: list, top_n: int = 5) -> dict:
    summary = {}
    for col in categorical_cols:
        vc = df[col].value_counts(dropna=True).head(top_n)
        summary[col] = {
            "n_unique": int(df[col].nunique(dropna=True)),
            "top_values": vc.to_dict(),
            "missing_pct": round(df[col].isna().mean() * 100, 2),
        }
    return summary


def correlation_matrix(df: pd.DataFrame, numeric_cols: list) -> pd.DataFrame:
    if len(numeric_cols) < 2:
        return pd.DataFrame()
    return df[numeric_cols].corr(numeric_only=True).round(3)


def find_strong_correlations(corr: pd.DataFrame, threshold: float = 0.6) -> list:
    """Return list of (col_a, col_b, corr_value) pairs above threshold, deduped."""
    pairs = []
    if corr.empty:
        return pairs
    cols = corr.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = corr.iloc[i, j]
            if pd.notna(val) and abs(val) >= threshold:
                pairs.append((cols[i], cols[j], round(float(val), 3)))
    return sorted(pairs, key=lambda x: -abs(x[2]))


def detect_outliers_iqr(df: pd.DataFrame, numeric_cols: list) -> dict:
    """IQR-based outlier detection per numeric column."""
    outlier_info = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = series[(series < lower) | (series > upper)]
        if len(outliers) > 0:
            outlier_info[col] = {
                "count": int(len(outliers)),
                "pct": round(len(outliers) / len(series) * 100, 2),
                "bounds": (round(float(lower), 2), round(float(upper), 2)),
            }
    return outlier_info


def group_performance(df: pd.DataFrame, categorical_cols: list, numeric_cols: list,
                       max_groups_cardinality: int = 25) -> dict:
    """
    For each (categorical, numeric) pair with reasonable cardinality, compute
    group means/sums so we can surface 'top' and 'bottom' performing segments -
    the core of most business insight reports (e.g. best/worst region, product, channel).
    """
    results = {}
    for cat in categorical_cols:
        if df[cat].nunique(dropna=True) > max_groups_cardinality:
            continue
        for num in numeric_cols:
            grouped = df.groupby(cat, observed=True)[num].agg(["mean", "sum", "count"])
            grouped = grouped.sort_values("sum", ascending=False)
            if len(grouped) < 2:
                continue
            results[f"{num} by {cat}"] = grouped.round(2)
    return results


def time_trend_analysis(df: pd.DataFrame, datetime_cols: list, numeric_cols: list) -> dict:
    """
    For each datetime column, resample numeric metrics monthly and compute a
    simple linear trend (slope) to classify direction: growing / declining / flat.
    """
    trends = {}
    for dt_col in datetime_cols:
        temp = df.dropna(subset=[dt_col]).set_index(dt_col).sort_index()
        if temp.empty:
            continue
        for num in numeric_cols:
            monthly = temp[num].resample("ME").sum(min_count=1).dropna()
            if len(monthly) < 3:
                continue
            x = np.arange(len(monthly))
            y = monthly.values
            slope, intercept = np.polyfit(x, y, 1)
            pct_change = ((y[-1] - y[0]) / abs(y[0]) * 100) if y[0] != 0 else 0
            direction = "growing" if slope > 0 and pct_change > 5 else \
                        "declining" if slope < 0 and pct_change < -5 else "flat"
            trends[f"{num} over {dt_col}"] = {
                "series": monthly,
                "slope": float(slope),
                "pct_change": round(float(pct_change), 1),
                "direction": direction,
            }
    return trends
