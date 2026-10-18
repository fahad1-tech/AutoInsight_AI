"""
visualizer.py
-------------
Generates all charts as base64-encoded PNGs so the final report is a single
self-contained HTML file (no external image files to manage/host).
"""

import io
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.autolayout"] = True


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def chart_missing_values(missing_df: pd.DataFrame) -> str:
    if missing_df.empty:
        return ""
    fig, ax = plt.subplots(figsize=(7, max(2, len(missing_df) * 0.4)))
    sns.barplot(x=missing_df["missing_pct"], y=missing_df.index, ax=ax, color="#e07a5f")
    ax.set_xlabel("Missing (%)")
    ax.set_ylabel("")
    ax.set_title("Missing Data by Column")
    return _fig_to_base64(fig)


def chart_correlation_heatmap(corr: pd.DataFrame) -> str:
    if corr.empty:
        return ""
    fig, ax = plt.subplots(figsize=(max(5, len(corr) * 0.8), max(4, len(corr) * 0.7)))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0,
                square=True, ax=ax, cbar_kws={"shrink": 0.8})
    ax.set_title("Correlation Matrix")
    return _fig_to_base64(fig)


def chart_numeric_distribution(df: pd.DataFrame, col: str) -> str:
    values = df[col].dropna()
    if len(values) > 50000:
        values = values.sample(50000, random_state=0)
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(values, kde=True, ax=ax, color="#3d5a80")
    ax.set_title(f"Distribution of {col}")
    ax.set_xlabel(col)
    return _fig_to_base64(fig)


def chart_categorical_bar(df: pd.DataFrame, col: str, top_n: int = 10) -> str:
    vc = df[col].value_counts(dropna=True).head(top_n)
    fig, ax = plt.subplots(figsize=(7, max(2.5, len(vc) * 0.4)))
    sns.barplot(x=vc.values, y=vc.index.astype(str), ax=ax, color="#81b29a")
    ax.set_xlabel("Count")
    ax.set_title(f"Top {min(top_n, len(vc))} categories in {col}")
    return _fig_to_base64(fig)

def chart_group_performance(grouped: pd.DataFrame, title: str, top_n: int = 10) -> str:
    data = grouped.head(top_n)
    fig, ax = plt.subplots(figsize=(7, max(2.5, len(data) * 0.4)))
    sns.barplot(x=data["sum"], y=data.index.astype(str), ax=ax, color="#f2cc8f")
    ax.set_xlabel("Total")
    ax.set_title(title)
    return _fig_to_base64(fig)


def chart_time_trend(series: pd.Series, title: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(series.index, series.values, marker="o", color="#3d5a80", linewidth=2)
    ax.fill_between(series.index, series.values, alpha=0.1, color="#3d5a80")
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=45)
    return _fig_to_base64(fig)


def chart_scatter(df: pd.DataFrame, col_a: str, col_b: str) -> str:
    if len(df) > 5000:
        df = df.sample(5000, random_state=0)
    fig, ax = plt.subplots(figsize=(6, 4.5))
    sns.scatterplot(data=df, x=col_a, y=col_b, ax=ax, alpha=0.6, color="#e07a5f")
    sns.regplot(data=df, x=col_a, y=col_b, ax=ax, scatter=False, color="#3d5a80")
    ax.set_title(f"{col_a} vs {col_b}")
    return _fig_to_base64(fig)


def chart_churn_overview(overall_rate: float) -> str:
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    ax.pie([overall_rate, 1 - overall_rate], labels=["Churned", "Retained"],
           colors=["#e63946", "#2a9d8f"], startangle=90, autopct="%1.1f%%",
           wedgeprops={"width": 0.42, "edgecolor": "white"}, textprops={"fontsize": 10})
    ax.set_title("Churned vs Retained")
    return _fig_to_base64(fig)


def chart_churn_by_segment(table: pd.DataFrame, feature: str, overall: float,
                           kind: str = "categorical", top_n: int = 10) -> str:
    title = f"Churn rate by {feature}  (dashed line = average {overall*100:.1f}%)"
    data = table.head(top_n) if kind == "categorical" else table
    colors = ["#e63946" if r > overall else "#2a9d8f" for r in data["churn_rate"]]
    if kind == "numeric":
        fig, ax = plt.subplots(figsize=(7, 4.2))
        ax.bar(data["segment"], data["churn_rate"] * 100, color=colors)
        ax.axhline(overall * 100, color="#22223b", linestyle="--", linewidth=1.2)
        for x_pos, (rate, n) in enumerate(zip(data["churn_rate"], data["n"])):
            ax.text(x_pos, rate * 100 + 0.8, f"{rate*100:.1f}%", ha="center", fontsize=8)
        ax.set_ylim(0, min(max(data["churn_rate"].max() * 100 * 1.2, overall * 100 * 1.2), 108))
        ax.set_ylabel("Churn rate (%)")
        ax.set_xlabel(f"{feature} (value bands)")
        ax.tick_params(axis="x", rotation=25 if len(data) > 4 else 0)
    else:
        fig, ax = plt.subplots(figsize=(7, max(2.8, len(data) * 0.45)))
        ax.barh(data["segment"], data["churn_rate"] * 100, color=colors)
        ax.axvline(overall * 100, color="#22223b", linestyle="--", linewidth=1.2)
        for y_pos, (rate, n) in enumerate(zip(data["churn_rate"], data["n"])):
            ax.text(rate * 100 + 0.5, y_pos, f"{rate*100:.1f}%  (n={int(n):,})", va="center", fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, max(data["churn_rate"].max() * 100 * 1.35, overall * 100 * 1.3))
        ax.set_xlabel("Churn rate (%)")
    ax.set_title(title, fontsize=10)
    return _fig_to_base64(fig)


def chart_driver_ranking(importance: list, top_n: int = 10) -> str:
    """importance: list of (feature, strength, relative_pct, kind), strongest first."""
    rows = importance[:top_n]
    fig, ax = plt.subplots(figsize=(7, max(3, len(rows) * 0.45)))
    colors = ["#e63946" if i == 0 else "#3d5a80" for i in range(len(rows))]
    ax.barh([r[0] for r in rows], [r[2] for r in rows], color=colors)
    for y_pos, r in enumerate(rows):
        ax.text(r[2] + 1, y_pos, f"{r[2]:.0f}%", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 115)
    ax.set_xlabel("Relative driver strength (strongest = 100%)")
    ax.set_title("Which columns separate churners from loyal customers?", fontsize=10)
    return _fig_to_base64(fig)


def chart_overlay_distribution(data: pd.DataFrame, col: str, y: pd.Series) -> str:
    d = pd.DataFrame({"v": data[col], "churn": y}).dropna()
    if len(d) > 60000:
        d = d.sample(60000, random_state=0)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for val, label, color in ((0, "Retained", "#2a9d8f"), (1, "Churned", "#e63946")):
        ax.hist(d.loc[d["churn"] == val, "v"], bins=30, density=True, alpha=0.55,
                color=color, label=label)
    ax.set_title(f"{col}: churned vs retained customers", fontsize=10)
    ax.set_xlabel(col)
    ax.set_ylabel("Share of customers (density)")
    ax.legend()
    return _fig_to_base64(fig)


def chart_risk_heatmap(labels_a, labels_b, y: pd.Series, name_a: str, name_b: str,
                       overall: float, min_n: int = 30) -> str:
    d = pd.DataFrame({"a": labels_a, "b": labels_b, "y": y})
    rate = d.pivot_table(index="a", columns="b", values="y", aggfunc="mean", observed=True)
    cnt = d.pivot_table(index="a", columns="b", values="y", aggfunc="count", observed=True)
    rate = (rate.where(cnt >= min_n) * 100)
    rate.index = [str(i) for i in rate.index]
    rate.columns = [str(c) for c in rate.columns]
    fig, ax = plt.subplots(figsize=(max(5.5, len(rate.columns) * 1.1), max(3.5, len(rate) * 0.7)))
    sns.heatmap(rate, annot=True, fmt=".0f", cmap="RdYlGn_r", center=overall * 100,
                cbar_kws={"label": "Churn rate (%)"}, ax=ax, linewidths=0.5)
    ax.set_xlabel(name_b)
    ax.set_ylabel(name_a)
    ax.set_title(f"Churn rate (%) by {name_a} and {name_b}", fontsize=10)
    return _fig_to_base64(fig)
