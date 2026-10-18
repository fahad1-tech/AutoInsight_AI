"""
pipeline.py
-----------
Orchestrates the full analysis: load -> classify columns -> EDA -> KPIs & insights ->
narrative -> charts -> HTML dashboard. Used by the CLI and importable from Python:

    from autoinsight.pipeline import run_pipeline
    run_pipeline(["data.csv"], "output/report.html")
"""

import os
import re
import sys

import pandas as pd

from . import ai_narrator, churn, data_loader, eda, report, visualizer
from . import insights as insights_mod
from . import kpis as kpi_mod

SEVERITY_ORDER = {"critical": 0, "watch": 1, "info": 2}


def clean_name(path: str) -> str:
    """Drop upload prefixes like '1791628642330_' from display names."""
    return re.sub(r"^\d{8,}_", "", os.path.basename(path))


def load_inputs(paths: list) -> pd.DataFrame:
    frames = [data_loader.load_csv(p) for p in paths]
    if len(frames) == 1:
        return frames[0]
    first = set(frames[0].columns)
    if all(set(f.columns) == first for f in frames):
        total = sum(len(f) for f in frames)
        print(f"      -> {len(frames)} files share the same columns; combining them ({total:,} rows)")
        return pd.concat(frames, ignore_index=True)
    sys.exit("ERROR: these files have different columns, so they cannot be stacked.\n"
             "Run them one at a time (a separate command per file), or merge them "
             "on a shared key column first.")


def churn_charts(res: dict) -> list:
    overall, y, data = res["overall_rate"], res["y"], res["data"]
    out = [(visualizer.chart_churn_overview(overall), "Overall churn split"),
           (visualizer.chart_driver_ranking(res["importance"]), "Driver ranking")]

    # combination heatmap of the two strongest drivers that have few enough groups
    pair = [(f, i) for f, i in res["ranked"] if i["labels"].nunique() <= 8][:2]
    if len(pair) == 2:
        (fa, ia), (fb, ib) = pair
        out.append((visualizer.chart_risk_heatmap(ia["labels"], ib["labels"], y, fa, fb, overall),
                    f"Where the risk is highest: {fa} x {fb}"))

    # churned vs retained distributions for the strongest continuous drivers
    cont = [f for f, i in res["ranked"] if i["kind"] == "numeric" and data[f].nunique() > 8][:3]
    for f in cont:
        out.append((visualizer.chart_overlay_distribution(data, f, y), f"{f}: churned vs retained"))

    for feat, info in res["ranked"][:6]:
        out.append((visualizer.chart_churn_by_segment(info["table"], feat, overall, info["kind"]),
                    f"Churn rate by {feat}"))
    return out


def run_pipeline(csv_paths: list, output_path: str, use_ai: bool = False,
                 target: str = None) -> str:
    print(f"[1/6] Loading data from {', '.join(csv_paths)} ...")
    df = load_inputs(csv_paths)
    columns = data_loader.classify_columns(df)
    profile = data_loader.profile_dataset(df)

    # ---- churn mode ----
    if target is None:
        target = churn.detect_target(df)
    elif target.lower() == "none":
        target = None
    elif target not in df.columns:
        sys.exit(f"ERROR: target column '{target}' not found. Columns: {list(df.columns)}")

    if target:
        print(f"      -> Churn mode ON (target column: '{target}')")
        for key in ("numeric", "categorical", "identifier"):
            columns[key] = [c for c in columns[key] if c != target]

    print(f"      -> {profile['n_rows']:,} rows, {profile['n_cols']} columns "
          f"({len(columns['numeric'])} numeric, {len(columns['categorical'])} categorical, "
          f"{len(columns['datetime'])} datetime, {len(columns['identifier'])} id/text ignored)")

    print("[2/6] Running automated EDA ...")
    missing_df = eda.missing_value_report(df)
    corr = eda.correlation_matrix(df, columns["numeric"])
    corr_pairs = eda.find_strong_correlations(corr)
    outliers = eda.detect_outliers_iqr(df, columns["numeric"])
    cat_summary = eda.categorical_summary(df, columns["categorical"])
    # Sums of metrics per segment are meaningless for churn data, so skip them in churn mode
    group_perf = {} if target else eda.group_performance(df, columns["categorical"], columns["numeric"])
    trends = eda.time_trend_analysis(df, columns["datetime"], columns["numeric"])

    churn_res = None
    if target:
        churn_res = churn.analyze_churn(df, target, columns["categorical"], columns["numeric"])
        profile["churn_rate"] = churn_res["overall_rate"]

    print("[3/6] Choosing KPIs and generating insights ...")
    if churn_res:
        kpi_list, kpi_focus = kpi_mod.churn_kpis(churn_res, columns)
    else:
        kpi_list, kpi_focus = kpi_mod.generic_kpis(df, columns, trends)
    print("      -> KPIs: " + " | ".join(k["label"] for k in kpi_list))

    findings = insights_mod.generate_insights(
        profile, missing_df, corr_pairs, outliers, group_perf, trends, cat_summary)
    if churn_res:
        findings = churn.churn_insights(churn_res) + findings
        findings.sort(key=lambda i: SEVERITY_ORDER.get(i.severity, 3))
    print(f"      -> {len(findings)} insights generated")

    print("[4/6] Writing executive narrative "
          f"({'Claude API' if use_ai and ai_narrator.is_available() else 'rule-based fallback'}) ...")
    dataset_name = ", ".join(clean_name(p) for p in csv_paths)
    narrative = ai_narrator.generate_narrative(profile, findings, dataset_name) if use_ai \
        else ai_narrator._fallback_narrative(profile, findings)

    print("[5/6] Rendering charts ...")
    charts = {}
    if churn_res:
        charts["Churn Drivers"] = churn_charts(churn_res)

    charts["Data Quality"] = ([(visualizer.chart_missing_values(missing_df), "Missing values by column")]
                              if not missing_df.empty else [])
    charts["Numeric Distributions"] = [
        (visualizer.chart_numeric_distribution(df, col), f"Distribution: {col}")
        for col in columns["numeric"][:6]]
    charts["Category Breakdown"] = [
        (visualizer.chart_categorical_bar(df, col), f"Top categories: {col}")
        for col in columns["categorical"][:4]]
    corr_charts = []
    if not corr.empty:
        corr_charts.append((visualizer.chart_correlation_heatmap(corr), "Correlation matrix"))
    for a, b, v in corr_pairs[:2]:
        corr_charts.append((visualizer.chart_scatter(df, a, b), f"{a} vs {b} (r={v})"))
    charts["Relationships"] = corr_charts
    charts["Segment Performance"] = [
        (visualizer.chart_group_performance(grouped, label), label)
        for label, grouped in list(group_perf.items())[:4]]
    charts["Trends Over Time"] = [
        (visualizer.chart_time_trend(t["series"], label), label) for label, t in trends.items()]

    print("[6/6] Building final report ...")
    html = report.build_report(dataset_name, profile, narrative, findings, charts,
                               kpis=kpi_list, kpi_focus=kpi_focus)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDone. Report saved to: {output_path}")
    return output_path
