"""
report.py
---------
Builds the single-file HTML dashboard: fixed sidebar navigation, one page per
section, dataset-specific KPI cards, and a "most useful KPI" callout.
Opens by double-click -- no server, no internet, no framework.
"""

from datetime import datetime
import html as html_lib

SEVERITY_COLORS = {"critical": "#e63946", "watch": "#f4a261", "info": "#2a9d8f"}
TONE_COLORS = {"bad": "#e63946", "warn": "#d98320", "good": "#2a9d8f", "neutral": "#3d5a80"}

ICONS = {
    "overview": '<path d="M3 3h8v8H3z"/><path d="M13 3h8v5h-8z"/><path d="M13 10h8v11h-8z"/><path d="M3 13h8v8H3z"/>',
    "insights": '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.2 1 2.3h6c0-1.1.4-1.8 1-2.3A7 7 0 0 0 12 2z"/>',
    "churn": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M17 8l5 5"/><path d="M22 8l-5 5"/>',
    "quality": '<path d="M12 2 2 20h20L12 2z"/><path d="M12 9v5"/><path d="M12 17h.01"/>',
    "distributions": '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20v-3"/>',
    "categories": '<path d="M12 2v10l8.5 5A10 10 0 1 0 12 2z"/><path d="M12 12 3.5 17"/>',
    "relationships": '<circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="M8.5 8.5 15.5 15.5"/><circle cx="18" cy="6" r="3"/><path d="M9 7.5 15.5 6"/>',
    "segments": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "trends": '<path d="M3 17 9 11l4 4 8-8"/><path d="M15 7h6v6"/>',
    "money": '<circle cx="12" cy="12" r="9"/><path d="M14.5 9.2c-.4-.8-1.4-1.2-2.5-1.2-1.4 0-2.5.8-2.5 1.9 0 2.7 5 1.2 5 4 0 1.1-1.1 1.9-2.5 1.9-1.1 0-2.1-.5-2.5-1.3"/><path d="M12 6.5V8"/><path d="M12 16v1.5"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "gauge": '<path d="M4 18a9 9 0 1 1 16 0"/><path d="M12 14l4-4"/><circle cx="12" cy="14" r="1"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17" cy="9" r="2.5"/><path d="M16 14.2a5 5 0 0 1 5.5 4.8"/>',
}

PAGE_META = [
    ("overview", "Overview", "overview"),
    ("insights", "Insights", "insights"),
    ("Churn Drivers", "Churn Drivers", "churn"),
    ("Data Quality", "Data Quality", "quality"),
    ("Numeric Distributions", "Distributions", "distributions"),
    ("Category Breakdown", "Categories", "categories"),
    ("Relationships", "Relationships", "relationships"),
    ("Segment Performance", "Segments", "segments"),
    ("Trends Over Time", "Trends", "trends"),
]

CSS = """
:root { --ink:#22223b; --muted:#6c6c80; --bg:#f5f6f8; --card:#ffffff; --accent:#3d5a80; --sidebar:#1f2a3d; }
* { box-sizing:border-box; }
body { font-family:'Segoe UI',-apple-system,Arial,sans-serif; background:var(--bg); color:var(--ink); margin:0; }
.sidebar { position:fixed; top:0; left:0; width:230px; height:100vh; background:linear-gradient(180deg,var(--sidebar),#151d2b); color:#c8d1dc; overflow-y:auto; z-index:10; }
.sidebar .brand { padding:22px 20px; font-weight:700; font-size:16px; color:#fff; border-bottom:1px solid rgba(255,255,255,0.08); display:flex; align-items:center; gap:8px; }
.nav-item { display:flex; align-items:center; gap:12px; padding:13px 20px; cursor:pointer; font-size:14px; border-left:3px solid transparent; transition:background 0.15s; }
.nav-item svg { flex-shrink:0; opacity:0.85; }
.nav-item:hover { background:rgba(255,255,255,0.06); }
.nav-item.active { background:rgba(255,255,255,0.09); border-left-color:#7ea8d8; color:#fff; }
.sidebar-footer { padding:16px 20px; font-size:11px; color:#7c8aa0; border-top:1px solid rgba(255,255,255,0.08); margin-top:20px; }
.main { margin-left:230px; padding:28px 40px 60px 40px; max-width:1240px; }
.topbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; color:var(--muted); font-size:13px; }
.page { display:none; }
.page.active { display:block; animation:fadeIn 0.2s ease; }
@keyframes fadeIn { from {opacity:0; transform:translateY(4px);} to {opacity:1; transform:translateY(0);} }
.page-header { display:flex; align-items:center; gap:10px; margin:6px 0 20px 0; color:var(--accent); }
.page-header h1 { margin:0; font-size:22px; color:var(--ink); }
.page-subtitle { color:var(--muted); font-size:13px; margin:-12px 0 20px 0; }
h2 { font-size:16px; border-bottom:3px solid var(--accent); display:inline-block; padding-bottom:4px; margin-top:34px; }
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:16px; margin-top:6px; }
.kpi-card { background:var(--card); border-radius:14px; padding:18px 20px; box-shadow:0 2px 12px rgba(0,0,0,0.07); border-top:4px solid var(--tone); position:relative; }
.kpi-top { display:flex; align-items:center; justify-content:space-between; min-height:30px; }
.kpi-icon { width:30px; height:30px; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; background:color-mix(in srgb, var(--tone) 14%, white); color:var(--tone); }
.kpi-badge { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; background:#fff4d6; color:#9a6b00; padding:3px 9px; border-radius:10px; }
.kpi-value { font-size:30px; font-weight:700; color:var(--tone); margin-top:10px; line-height:1.1; }
.kpi-label { font-size:13px; font-weight:600; margin-top:6px; }
.kpi-sub { font-size:12px; color:var(--muted); margin-top:4px; line-height:1.4; }
.focus-box { background:#fffaf0; border:1px solid #f3dca8; border-left:5px solid #e0a31a; border-radius:10px; padding:16px 20px; margin-top:18px; font-size:14px; line-height:1.55; display:flex; gap:14px; }
.focus-box svg { color:#c98a00; flex-shrink:0; margin-top:2px; }
.focus-box .rank { margin-top:8px; font-size:12.5px; color:#6b5b2a; }
.health { display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }
.pill { background:#e9edf3; color:#445; font-size:12px; padding:5px 12px; border-radius:14px; }
.metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:16px; }
.metric-box { background:var(--card); border-radius:12px; padding:18px 20px; box-shadow:0 2px 10px rgba(0,0,0,0.06); }
.metric-box .num { font-size:24px; font-weight:700; color:var(--accent); }
.metric-box .label { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:0.03em; margin-top:2px; }
.narrative-box { background:var(--card); border-left:5px solid var(--accent); padding:20px 24px; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.05); line-height:1.6; font-size:14px; }
.insight-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; margin-top:14px; }
.insight-card { background:var(--card); border-radius:10px; padding:16px 20px; margin-bottom:14px; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
.insight-card.compact { margin-bottom:0; }
.insight-head { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.insight-head h3 { margin:0; font-size:15px; }
.insight-card p { margin:8px 0 0 0; font-size:13.5px; line-height:1.5; color:#333; }
.view-all { display:inline-block; margin-top:16px; color:var(--accent); font-weight:600; font-size:13px; cursor:pointer; }
.chart-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:20px; margin-top:6px; }
.chart { background:var(--card); border-radius:10px; padding:14px; box-shadow:0 2px 10px rgba(0,0,0,0.05); text-align:center; }
.chart img { max-width:100%; border-radius:6px; }
.caption { font-size:12px; color:var(--muted); margin-top:8px; }
.empty-state { color:var(--muted); font-style:italic; }
@media (max-width: 820px) {
  .sidebar { width:64px; }
  .sidebar .brand span, .nav-item span, .sidebar-footer { display:none; }
  .main { margin-left:64px; padding:20px; }
  .chart-grid { grid-template-columns:1fr; }
}
"""

JS = """
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  document.querySelector('.nav-item[data-page="' + id + '"]').classList.add('active');
  window.scrollTo(0, 0);
}
"""


def _icon(key: str, size: int = 18) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{ICONS.get(key, "")}</svg>')


def _badge(severity: str) -> str:
    color = SEVERITY_COLORS.get(severity, "#999")
    return (f'<span style="background:{color};color:white;padding:2px 10px;border-radius:12px;'
            f'font-size:12px;font-weight:600;text-transform:uppercase;">{severity}</span>')


def _img(b64: str, caption: str = "") -> str:
    if not b64:
        return ""
    cap = f'<div class="caption">{html_lib.escape(caption)}</div>' if caption else ""
    return f'<div class="chart"><img src="data:image/png;base64,{b64}" />{cap}</div>'


def _chart_page(title: str, icon_key: str, imgs: list, subtitle: str = "") -> str:
    body = "".join(_img(b64, cap) for b64, cap in imgs) if imgs else \
        "<p class='empty-state'>Nothing to show for this dataset.</p>"
    sub = f'<p class="page-subtitle">{html_lib.escape(subtitle)}</p>' if subtitle else ""
    return (f'<section class="page-header">{_icon(icon_key, 24)}<h1>{html_lib.escape(title)}</h1></section>'
            f'{sub}<div class="chart-grid">{body}</div>')


def _kpi_card(k: dict) -> str:
    color = TONE_COLORS.get(k.get("tone", "neutral"), TONE_COLORS["neutral"])
    badge = f'<span class="kpi-badge">&#9733; {html_lib.escape(k["badge"])}</span>' if k.get("badge") else ""
    return (f'<div class="kpi-card" style="--tone:{color}">'
            f'<div class="kpi-top"><span class="kpi-icon">{_icon(k.get("icon", "target"), 17)}</span>{badge}</div>'
            f'<div class="kpi-value">{html_lib.escape(str(k["value"]))}</div>'
            f'<div class="kpi-label">{html_lib.escape(k["label"])}</div>'
            f'<div class="kpi-sub">{html_lib.escape(k.get("sub", ""))}</div></div>')


def build_report(dataset_name: str, profile: dict, narrative: str, insights: list,
                 charts: dict, kpis: list = None, kpi_focus: dict = None) -> str:
    generated_at = datetime.now().strftime("%B %d, %Y at %H:%M")
    n_critical = sum(1 for i in insights if i.severity == "critical")
    n_watch = sum(1 for i in insights if i.severity == "watch")
    is_churn = profile.get("churn_rate") is not None

    # ---------- Overview ----------
    if kpis:
        kpi_html = ('<h2>Key Performance Indicators</h2><div class="kpi-grid">'
                    + "".join(_kpi_card(k) for k in kpis) + '</div>')
    else:
        kpi_html = (f'<div class="metrics"><div class="metric-box"><div class="num">{profile["n_rows"]:,}</div>'
                    f'<div class="label">Rows</div></div></div>')

    focus_html = ""
    if kpi_focus:
        rank = ""
        if kpi_focus.get("ranking"):
            rank = ('<div class="rank"><strong>Driver ranking:</strong> '
                    + " &rsaquo; ".join(f"{html_lib.escape(str(f))} ({r:.0f}%)" for f, r in kpi_focus["ranking"])
                    + '</div>')
        focus_html = (f'<div class="focus-box">{_icon("insights", 22)}<div>'
                      f'<strong>Most useful KPI for this dataset: {html_lib.escape(kpi_focus["label"])}</strong><br>'
                      f'{html_lib.escape(kpi_focus["reason"])}{rank}</div></div>')

    health_html = (f'<div class="health"><span class="pill">{profile["n_rows"]:,} rows</span>'
                   f'<span class="pill">{profile["n_cols"]} columns</span>'
                   f'<span class="pill">{profile["missing_total_pct"]}% missing</span>'
                   f'<span class="pill">{profile["duplicate_rows"]} duplicate rows</span>'
                   f'<span class="pill">{len(insights)} insights</span></div>')

    narrative_html = html_lib.escape(narrative).replace("\n", "<br>")
    top_preview = "".join(f"""
        <div class="insight-card compact">
          <div class="insight-head"><h3>{html_lib.escape(i.title)}</h3>{_badge(i.severity)}</div>
          <p>{html_lib.escape(i.finding)}</p>
        </div>""" for i in insights[:3])
    view_all = ("<h2>Top Findings</h2><div class='insight-grid'>" + top_preview +
                "</div><a class='view-all' onclick=\"showPage('insights')\">View all insights &rarr;</a>"
                if top_preview else "")

    overview_page = f"""
    <section class="page-header">{_icon('overview', 24)}<h1>Overview</h1></section>
    {kpi_html}{focus_html}{health_html}
    <h2>Executive Summary</h2>
    <div class="narrative-box">{narrative_html}</div>
    {view_all}"""

    # ---------- Insights ----------
    insight_cards = "".join(f"""
        <div class="insight-card">
          <div class="insight-head"><h3>{html_lib.escape(i.title)}</h3>{_badge(i.severity)}</div>
          <p><strong>Finding:</strong> {html_lib.escape(i.finding)}</p>
          <p><strong>Business impact:</strong> {html_lib.escape(i.business_problem)}</p>
          <p><strong>Recommended action:</strong> {html_lib.escape(i.recommendation)}</p>
        </div>""" for i in insights)
    insights_page = f"""
    <section class="page-header">{_icon('insights', 24)}<h1>Insights &amp; Recommendations</h1></section>
    <p class="page-subtitle">{n_critical} critical &middot; {n_watch} to watch &middot; {len(insights) - n_critical - n_watch} informational</p>
    {insight_cards if insight_cards else "<p class='empty-state'>No notable issues detected -- this dataset looks clean.</p>"}"""

    # ---------- Sidebar + pages ----------
    nav_items, page_divs = [], []
    for key, label, icon_key in PAGE_META:
        if key == "overview":
            content, has_content = overview_page, True
        elif key == "insights":
            content, has_content = insights_page, True
        else:
            imgs = charts.get(key, [])
            has_content = bool(imgs)
            subtitle = ("Red bars churn more than average, green bars less. Wider gaps mean a stronger driver."
                        if key == "Churn Drivers" else "")
            content = _chart_page(label, icon_key, imgs, subtitle)
        if not has_content:
            continue
        active = "active" if key == "overview" else ""
        nav_items.append(f'<div class="nav-item {active}" data-page="{key}" onclick="showPage(\'{key}\')">'
                         f'{_icon(icon_key)}<span>{html_lib.escape(label)}</span></div>')
        page_divs.append(f'<div class="page {active}" id="page-{key}">{content}</div>')

    nav_html = "\n".join(nav_items)
    pages_html = "\n".join(page_divs)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AutoInsight AI Dashboard - {html_lib.escape(dataset_name)}</title>
<style>{CSS}</style>
</head>
<body>
<nav class="sidebar">
  <div class="brand">{_icon('overview', 20)}<span>AutoInsight AI</span></div>
  {nav_html}
  <div class="sidebar-footer">Generated {generated_at}</div>
</nav>
<main class="main">
  <div class="topbar"><span>Dataset: <strong>{html_lib.escape(dataset_name)}</strong></span><span>{generated_at}</span></div>
  {pages_html}
</main>
<script>{JS}</script>
</body>
</html>"""
