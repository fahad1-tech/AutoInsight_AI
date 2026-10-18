"""
insights.py
-----------
This is the "analyst brain" of the project. It turns raw statistics (from eda.py)
into plain-English findings, each tagged with:
  - severity (info / watch / critical)
  - a business problem statement
  - a suggested action

Every insight is fully rule-based and reproducible (no LLM required), which
matters for a portfolio project: it proves the analytical logic itself, not
just prompting. ai_narrator.py optionally layers a natural-language summary
on top using Claude.
"""

from dataclasses import dataclass, field


@dataclass
class Insight:
    title: str
    finding: str
    business_problem: str
    recommendation: str
    severity: str = "info"  # info | watch | critical


def generate_insights(profile: dict, missing_df, corr_pairs: list, outliers: dict,
                       group_perf: dict, trends: dict, categorical_summary: dict) -> list:
    insights: list[Insight] = []

    # --- Data quality ---
    if profile["duplicate_rows"] > 0:
        pct = round(profile["duplicate_rows"] / profile["n_rows"] * 100, 1)
        insights.append(Insight(
            title="Duplicate Records Detected",
            finding=f"{profile['duplicate_rows']} duplicate rows found ({pct}% of the dataset).",
            business_problem="Duplicate records can inflate totals, distort averages, and "
                              "lead to double-counted revenue/customers in downstream reporting.",
            recommendation="De-duplicate at the source system and add a uniqueness "
                            "constraint or ETL dedup step before this data reaches reporting.",
            severity="critical" if pct > 5 else "watch",
        ))

    if not missing_df.empty:
        worst = missing_df.iloc[0]
        insights.append(Insight(
            title="Missing Data",
            finding=f"'{missing_df.index[0]}' has the most missing values "
                    f"({worst['missing_pct']}% missing); {len(missing_df)} column(s) affected overall.",
            business_problem="Missing values bias averages, break joins, and can silently "
                              "exclude records from segment-level analysis.",
            recommendation="Investigate root cause (form validation, integration gap, "
                            "optional field) and decide on an explicit imputation or "
                            "exclusion policy rather than letting it default silently.",
            severity="critical" if worst["missing_pct"] > 30 else "watch",
        ))

    # --- Outliers ---
    for col, info in outliers.items():
        insights.append(Insight(
            title=f"Outliers in {col}",
            finding=f"{info['count']} values ({info['pct']}%) fall outside the expected "
                    f"range ({info['bounds'][0]} to {info['bounds'][1]}).",
            business_problem=f"Extreme values in '{col}' can be genuine (VIP customers, "
                              f"bulk orders) or data entry errors -- either way they distort "
                              f"averages used for planning and forecasting.",
            recommendation=f"Segment '{col}' outliers separately in reporting (don't let them "
                            f"skew the 'typical' customer/transaction view), and validate a "
                            f"sample against source records.",
            severity="watch" if info["pct"] < 5 else "critical",
        ))

    # --- Correlations ---
    for col_a, col_b, val in corr_pairs[:5]:
        direction = "positively" if val > 0 else "negatively"
        insights.append(Insight(
            title=f"Strong relationship: {col_a} & {col_b}",
            finding=f"'{col_a}' and '{col_b}' are strongly {direction} correlated (r = {val}).",
            business_problem=f"If this relationship is causal, changes in '{col_a}' could "
                              f"be used to predict or influence '{col_b}' -- an untapped "
                              f"lever for planning or pricing decisions.",
            recommendation=f"Validate causality (not just correlation) via a controlled test, "
                            f"then consider using '{col_a}' as a leading indicator or input "
                            f"feature for forecasting '{col_b}'.",
            severity="info",
        ))

    # --- Group performance (best/worst segments) ---
    for label, grouped in group_perf.items():
        top = grouped.index[0]
        bottom = grouped.index[-1]
        top_val, bottom_val = grouped.iloc[0]["sum"], grouped.iloc[-1]["sum"]
        if bottom_val == 0 or top_val == bottom_val:
            continue
        gap_pct = round((top_val - bottom_val) / (abs(bottom_val) + 1e-9) * 100, 1)
        insights.append(Insight(
            title=f"Performance Gap: {label}",
            finding=f"'{top}' leads with {top_val:,.0f}, while '{bottom}' trails at "
                    f"{bottom_val:,.0f} -- a {gap_pct:,.0f}% gap.",
            business_problem=f"Uneven performance across segments in '{label}' suggests "
                              f"either an opportunity being under-served or an operational "
                              f"issue dragging down '{bottom}'.",
            recommendation=f"Study what '{top}' is doing differently (pricing, marketing "
                            f"mix, staffing) and pilot those tactics in '{bottom}' before "
                            f"a full rollout.",
            severity="watch" if gap_pct > 100 else "info",
        ))

    # --- Trends over time ---
    for label, t in trends.items():
        if t["direction"] == "flat":
            continue
        insights.append(Insight(
            title=f"Trend: {label} is {t['direction']}",
            finding=f"'{label}' changed {t['pct_change']:+.1f}% from the first to the last "
                    f"period in the data.",
            business_problem="A sustained decline threatens revenue/engagement targets; "
                              "a sustained rise may require capacity or inventory planning."
                              if t["direction"] == "declining" else
                              "Sustained growth is good news but can strain capacity, "
                              "inventory, or support resources if unplanned.",
            recommendation="Investigate the driver behind this trend (seasonality, "
                            "campaign, churn, supply issue) and build it into the next "
                            "forecast/budget cycle rather than treating it as one-off."
                            if t["direction"] == "declining" else
                            "Confirm the growth driver is durable, then plan capacity, "
                            "stock, or headcount ahead of the curve rather than reactively.",
            severity="critical" if t["direction"] == "declining" and abs(t["pct_change"]) > 20 else "watch",
        ))

    # --- Categorical concentration risk ---
    for col, info in categorical_summary.items():
        if not info["top_values"]:
            continue
        top_val_count = list(info["top_values"].values())[0]
        total_known = sum(info["top_values"].values())
        if total_known == 0:
            continue
        share = top_val_count / total_known
        if info["n_unique"] > 1 and share > 0.5:
            top_name = list(info["top_values"].keys())[0]
            insights.append(Insight(
                title=f"Concentration Risk in {col}",
                finding=f"A single value ('{top_name}') accounts for over "
                        f"{share*100:.0f}% of records in '{col}' (among top categories shown).",
                business_problem="Heavy reliance on one segment, channel, or customer "
                                  "increases exposure if that single driver weakens.",
                recommendation="Actively diversify acquisition/revenue sources so no "
                                "single segment can materially disrupt performance if it declines.",
                severity="watch",
            ))

    # Sort: critical first, then watch, then info
    order = {"critical": 0, "watch": 1, "info": 2}
    insights.sort(key=lambda i: order.get(i.severity, 3))
    return insights
