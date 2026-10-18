"""
churn.py
--------
Target-aware (churn) analysis. When a binary churn column is present, this
module answers the questions a churn analyst actually asks:
  - What is the overall churn rate?
  - Which segments / value ranges churn far more (or less) than average?
  - Which features separate churners from loyal customers the most?
  - Which numeric metrics move together with churn?

Everything is plain pandas -- fully reproducible, no LLM needed.
"""

import numpy as np
import pandas as pd

from .insights import Insight

POSITIVE = {"yes", "y", "true", "1", "1.0", "churned", "churn", "left", "exited",
            "attrited customer", "cancelled", "canceled"}
NEGATIVE = {"no", "n", "false", "0", "0.0", "stayed", "retained", "active",
            "existing customer", "current"}
TARGET_HINTS = ("churn", "exited", "attrition", "attrited", "left")


def to_binary(series: pd.Series) -> pd.Series:
    """Convert a churn-like column (Yes/No, 1/0, True/False...) to 1.0 / 0.0 / NaN."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype(float)
    if pd.api.types.is_numeric_dtype(series):
        vals = set(series.dropna().unique())
        if vals and vals <= {0, 1}:
            return series.astype(float)
        return pd.Series(np.nan, index=series.index)
    s = series.astype(str).str.strip().str.lower()
    out = pd.Series(np.nan, index=series.index)
    out[s.isin(POSITIVE)] = 1.0
    out[s.isin(NEGATIVE)] = 0.0
    return out


def detect_target(df: pd.DataFrame):
    """Find a column that looks like a binary churn flag, or return None."""
    for col in df.columns:
        if any(h in col.lower() for h in TARGET_HINTS):
            b = to_binary(df[col])
            if b.notna().mean() > 0.9 and b.dropna().nunique() == 2:
                return col
    return None


def _strength(labels, y) -> float:
    """
    Driver strength = Cramer's V between a feature (segments / value bands) and churn.
    0 = the feature tells you nothing about who leaves, ~0.3+ = strong separation.
    Unlike a raw churn-rate gap it is comparable across features with different numbers of groups.
    """
    ct = pd.crosstab(labels, y)
    obs = ct.values.astype(float)
    obs = obs[obs.sum(axis=1) > 0]
    if obs.shape[0] < 2 or obs.shape[1] < 2:
        return 0.0
    n = obs.sum()
    exp = np.outer(obs.sum(axis=1), obs.sum(axis=0)) / n
    chi2 = ((obs - exp) ** 2 / exp).sum()
    return float(np.sqrt(chi2 / n))


def strength_label(v: float) -> str:
    return "strong" if v >= 0.3 else "moderate" if v >= 0.1 else "weak"


def analyze_churn(df: pd.DataFrame, target: str, categorical_cols: list,
                  numeric_cols: list, min_group: int = 30) -> dict:
    y_all = to_binary(df[target])
    valid = y_all.notna()
    y, data = y_all[valid], df[valid]
    overall = float(y.mean())

    features = {}

    def add(feature, labels, kind):
        strength = _strength(labels, y)
        g = y.groupby(labels, observed=True).agg(["mean", "count"])
        g = g[g["count"] >= min_group]
        if len(g) < 2:
            return
        g = g.reset_index()
        g.columns = ["segment", "churn_rate", "n"]
        g["segment"] = g["segment"].astype(str)
        if kind == "categorical":
            g = g.sort_values("churn_rate", ascending=False).reset_index(drop=True)
        g["lift"] = g["churn_rate"] / overall if overall > 0 else np.nan
        features[feature] = {
            "table": g,
            "kind": kind,
            "spread": float(g["churn_rate"].max() - g["churn_rate"].min()),
            "strength": strength,
            "labels": labels,
        }

    for col in categorical_cols:
        if col != target and data[col].nunique(dropna=True) <= 25:
            add(col, data[col], "categorical")

    for col in numeric_cols:
        if col == target:
            continue
        s = data[col]
        if s.nunique() < 2:
            continue
        labels = s if s.nunique() <= 8 else pd.qcut(s, q=4, duplicates="drop", precision=1)
        add(col, labels, "numeric")

    correlations = []
    for col in numeric_cols:
        if col == target or data[col].nunique() < 2:
            continue
        r = data[col].corr(y)
        if pd.notna(r):
            correlations.append((col, round(float(r), 3)))
    correlations.sort(key=lambda x: -abs(x[1]))

    ranked = sorted(features.items(), key=lambda kv: -kv[1]["strength"])
    max_s = max((i["strength"] for _, i in ranked), default=0) or 1.0
    importance = [(f, i["strength"], i["strength"] / max_s * 100, i["kind"]) for f, i in ranked]
    return {
        "y": y,
        "data": data,
        "importance": importance,
        "target": target,
        "overall_rate": overall,
        "n_total": int(len(y)),
        "n_churned": int(y.sum()),
        "features": features,
        "ranked": ranked,
        "correlations": correlations,
        "min_group": min_group,
    }


def churn_insights(res: dict) -> list:
    overall = res["overall_rate"]
    out = []

    sev = "critical" if overall >= 0.25 else "watch" if overall >= 0.10 else "info"
    out.append(Insight(
        title="Overall Churn Rate",
        finding=f"{overall*100:.1f}% of customers churned "
                f"({res['n_churned']:,} of {res['n_total']:,}).",
        business_problem="Each churned customer is lost recurring revenue plus the sunk "
                         "cost of acquiring them, and replacing a customer usually costs "
                         "far more than keeping one.",
        recommendation="Set a churn-reduction target and track it monthly by segment, "
                       "so retention work is aimed where churn is actually concentrated.",
        severity=sev,
    ))

    for feat, info in res["ranked"][:6]:
        if info["spread"] < 0.03:
            continue
        t = info["table"]
        hi = t.loc[t["churn_rate"].idxmax()]
        lo = t.loc[t["churn_rate"].idxmin()]
        sev = "critical" if (hi["churn_rate"] >= 0.5 or hi["lift"] >= 1.6) else "watch"
        if info["kind"] == "numeric":
            action = (f"Use '{feat}' in the range {hi['segment']} as an early-warning "
                      f"trigger: flag these customers in the CRM and route them to a "
                      f"retention team before they leave.")
        else:
            action = (f"Investigate why '{hi['segment']}' customers leave (pricing, product "
                      f"fit, service quality) and run a targeted retention offer for them; "
                      f"copy what works for '{lo['segment']}'.")
        out.append(Insight(
            title=f"Churn Driver: {feat}",
            finding=f"'{hi['segment']}' churns at {hi['churn_rate']*100:.1f}% versus "
                    f"{lo['churn_rate']*100:.1f}% for '{lo['segment']}' "
                    f"({hi['lift']:.1f}x the average, {int(hi['n']):,} customers).",
            business_problem=f"'{feat}' strongly separates loyal customers from at-risk "
                             f"ones, so a large share of lost revenue is concentrated in "
                             f"one identifiable group.",
            recommendation=action,
            severity=sev,
        ))

    # Highest-risk segments across all features
    rows = []
    for feat, info in res["features"].items():
        for _, r in info["table"].iterrows():
            if r["lift"] >= 1.3:
                rows.append((feat, r["segment"], r["churn_rate"], int(r["n"])))
    rows.sort(key=lambda x: -x[2])
    if rows:
        top = rows[:3]
        listing = "; ".join(f"{f} = {s} ({rate*100:.0f}%, {n:,} customers)"
                            for f, s, rate, n in top)
        out.append(Insight(
            title="Highest-Risk Customer Segments",
            finding=f"The riskiest pockets are: {listing}.",
            business_problem=f"These groups churn well above the {overall*100:.0f}% "
                             f"average, so retention spend aimed at them returns the most.",
            recommendation="Build a watch-list for these segments, assign an owner, and "
                           "test one retention action per segment (discount, outreach, "
                           "onboarding fix) with a control group to measure impact.",
            severity="watch",
        ))

    # Most loyal segment (what to learn from)
    best = None
    for feat, info in res["features"].items():
        for _, r in info["table"].iterrows():
            if best is None or r["churn_rate"] < best[2]:
                best = (feat, r["segment"], r["churn_rate"], int(r["n"]))
    if best and overall > 0 and best[2] <= overall * 0.7:
        out.append(Insight(
            title="Most Loyal Segment",
            finding=f"{best[0]} = {best[1]} has the lowest churn at {best[2]*100:.1f}% "
                    f"({best[3]:,} customers).",
            business_problem="Understanding why this group stays reveals what the "
                             "product or service does well.",
            recommendation=f"Study this group's behavior and move at-risk customers toward "
                           f"the same pattern (e.g. encourage '{best[1]}' where it is a choice).",
            severity="info",
        ))

    # Numeric signals
    for col, r in [c for c in res["correlations"] if abs(c[1]) >= 0.15][:3]:
        direction = "higher" if r > 0 else "lower"
        out.append(Insight(
            title=f"Churn Signal: {col}",
            finding=f"Higher '{col}' goes with {direction} churn (correlation r = {r}).",
            business_problem=f"'{col}' moves together with churn, making it a usable "
                             f"leading indicator of who is about to leave.",
            recommendation=f"Track '{col}' per customer and alert the retention team when "
                           f"it moves in the risky direction; include it in any churn "
                           f"prediction model.",
            severity="info",
        ))

    return out
