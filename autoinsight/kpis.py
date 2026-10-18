"""
kpis.py
-------
Chooses KPIs FROM THE DATA instead of showing the same boxes for every file.

Churn data  -> churn rate, value lost to churn (if a money column exists), plus one KPI
               for each of the columns that separate churners from loyal customers the most.
               The strongest one is flagged "Most useful KPI".
Other data  -> totals for money/volume columns, the dominant category, and the strongest trend.

Each KPI is a dict: label, value, sub, tone (bad|warn|good|neutral), icon, badge (optional).
"""

import re

import numpy as np

from .churn import strength_label

# Columns whose values can be summed into a meaningful total (money earned/spent, volumes)
MONEY_PRIORITY = ["revenue", "spend", "spent", "sales", "charge", "charges", "amount",
                  "balance", "income", "profit", "fee", "fees", "cost", "mrr"]
ADDITIVE_HINTS = set(MONEY_PRIORITY) | {"units", "quantity", "qty", "orders", "volume"}
# Columns where an AVERAGE is the right summary (adding prices or scores up is meaningless)
AVERAGE_HINTS = {"price", "arpu", "rate", "score", "rating", "satisfaction", "age", "tenure", "discount"}


def _tokens(name: str) -> set:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(name))
    return {t for t in re.split(r"[^a-zA-Z0-9]+", spaced.lower()) if t}


def fmt(x: float) -> str:
    x = float(x)
    a = abs(x)
    if a >= 1e9:
        return f"{x/1e9:.2f}B"
    if a >= 1e6:
        return f"{x/1e6:.2f}M"
    if a >= 1e4:
        return f"{x/1e3:.1f}K"
    if abs(x - round(x)) < 1e-9:
        return f"{x:,.0f}"
    return f"{x:,.1f}"


def _pick_money(numeric_cols: list, target: str):
    best, best_rank = None, 999
    for col in numeric_cols:
        if col == target:
            continue
        toks = _tokens(col)
        for rank, hint in enumerate(MONEY_PRIORITY):
            if hint in toks and rank < best_rank:
                best, best_rank = col, rank
    return best


def churn_kpis(res: dict, columns: dict):
    data, y, overall = res["data"], res["y"], res["overall_rate"]
    kpis = [dict(
        label="Churn rate", value=f"{overall*100:.1f}%",
        sub=f"{res['n_churned']:,} of {res['n_total']:,} customers left",
        tone="bad", icon="churn")]

    money = _pick_money(columns["numeric"], res["target"])
    if money:
        lost, total = float(data.loc[y == 1, money].sum()), float(data[money].sum())
        if total > 0:
            kpis.append(dict(
                label=f"{money} lost to churn", value=fmt(lost),
                sub=f"{lost/total*100:.0f}% of all {money} ({overall*100:.0f}% of customers)",
                tone="bad", icon="money"))

    focus = None
    for idx, (feat, info) in enumerate(res["ranked"][:4]):
        t = info["table"]
        if info["kind"] == "numeric" and data[feat].nunique() > 8:
            mc, mr = float(data.loc[y == 1, feat].mean()), float(data.loc[y == 0, feat].mean())
            delta = (mc - mr) / abs(mr) * 100 if mr else 0.0
            k = dict(label=f"Avg {feat} of churned customers", value=fmt(mc),
                     sub=f"vs {fmt(mr)} for retained customers ({delta:+.0f}%)",
                     tone="warn", icon="gauge")
        else:
            big = t[t["n"] >= max(30, 0.01 * res["n_total"])]
            big = t if big.empty else big
            hi = big.loc[big["churn_rate"].idxmax()]
            k = dict(label=f"Churn when {feat} = {hi['segment']}",
                     value=f"{hi['churn_rate']*100:.1f}%",
                     sub=f"{hi['lift']:.1f}x the average · {int(hi['n']):,} customers",
                     tone="bad", icon="target")
        if idx == 0:
            k["badge"] = "Most useful"
            focus = dict(
                label=k["label"],
                reason=(f"'{feat}' separates customers who leave from those who stay more "
                        f"clearly than any other column in this data (driver strength "
                        f"{info['strength']:.2f}, {strength_label(info['strength'])}). "
                        f"Track it first and use it as an early-warning signal."),
                ranking=[(f, rel) for f, _, rel, _ in res["importance"][:5]])
        kpis.append(k)
    return kpis, focus


def generic_kpis(df, columns: dict, trends: dict):
    kpis, nums = [], columns["numeric"]
    chosen = [c for c in nums if _tokens(c) & ADDITIVE_HINTS][:3]
    for c in chosen:
        s = df[c]
        kpis.append(dict(label=f"Total {c}", value=fmt(s.sum()),
                         sub=f"avg {fmt(s.mean())} per record · median {fmt(s.median())}",
                         tone="neutral", icon="money"))
    averaged = [c for c in nums if c not in chosen and _tokens(c) & AVERAGE_HINTS][:2]
    for c in averaged:
        s = df[c]
        kpis.append(dict(label=f"Average {c}", value=fmt(s.mean()),
                         sub=f"median {fmt(s.median())} · range {fmt(s.min())} to {fmt(s.max())}",
                         tone="neutral", icon="gauge"))
    chosen = chosen + averaged
    if len(chosen) < 3:
        rest = [c for c in nums if c not in chosen and df[c].mean() not in (0, np.nan)]
        rest.sort(key=lambda c: -(df[c].std() / abs(df[c].mean())) if df[c].mean() else 0)
        for c in rest[: 3 - len(chosen)]:
            s = df[c]
            kpis.append(dict(label=f"Average {c}", value=fmt(s.mean()),
                             sub=f"median {fmt(s.median())} · range {fmt(s.min())} to {fmt(s.max())}",
                             tone="neutral", icon="gauge"))
    for cat in columns["categorical"]:
        vc = df[cat].value_counts(normalize=True)
        if 1 < len(vc) <= 25:
            kpis.append(dict(label=f"Top {cat}: {vc.index[0]}", value=f"{vc.iloc[0]*100:.0f}%",
                             sub=f"of records ({len(vc)} different {cat} values)",
                             tone="neutral", icon="target"))
            break
    if trends:
        name, t = max(trends.items(), key=lambda kv: abs(kv[1]["pct_change"]))
        kpis.append(dict(label=name, value=f"{t['pct_change']:+.1f}%",
                         sub="change from first to last month",
                         tone="good" if t["pct_change"] > 0 else "bad", icon="trends"))
    focus = None
    if kpis:
        kpis[0]["badge"] = "Headline"
        focus = dict(label=kpis[0]["label"],
                     reason="This is the largest money or volume measure found in the data, "
                            "so it is the best single number to track over time.",
                     ranking=[])
    return kpis, focus
