# Architecture

## Data flow

`pipeline.run_pipeline()` runs these steps in order:

1. **Load** (`data_loader.load_csv`): reads one or more CSVs. Files with identical columns are stacked.
2. **Classify columns** (`data_loader.classify_columns`): each column becomes `numeric`, `categorical`, `datetime` or `identifier`. Row numbers, IDs and near-unique text such as surnames become identifiers and are ignored. 0/1 flags count as categorical.
3. **EDA** (`eda.py`): missing values, duplicates, correlations, IQR outliers, group performance, monthly trends.
4. **Churn analysis** (`churn.py`), only if a binary churn column exists. It groups every column into segments or value bands, computes churn rate per group and ranks columns by Cramér's V.
5. **KPIs** (`kpis.py`): `churn_kpis` for churn data, `generic_kpis` otherwise.
6. **Insights** (`insights.py`, `churn.churn_insights`): rule-based findings. Each has a finding, business problem, recommendation and severity.
7. **Narrative** (`ai_narrator.py`): rule-based summary, or Claude-written with `--use-ai`.
8. **Charts** (`visualizer.py`): matplotlib/seaborn images embedded as base64.
9. **Report** (`report.py`): one self-contained HTML file with sidebar navigation.

## Design choices

- **Computation and writing are separate.** Every number comes from pandas. The optional language model only rephrases computed findings, so results stay reproducible and testable.
- **No dataset-specific code.** Everything is derived from column types and content, so a new CSV needs no configuration.
- **One output file.** Charts are base64 images and the navigation is plain JavaScript, so the dashboard can be emailed or opened offline.

## Extending

**Add an insight rule.** In `insights.generate_insights` (or `churn.churn_insights`), append an `Insight(title, finding, business_problem, recommendation, severity)`.

**Add a KPI.** Return another dict from `kpis.churn_kpis` or `kpis.generic_kpis`:
`{"label", "value", "sub", "tone" (bad|warn|good|neutral), "icon"}`. Icons live in `report.ICONS`.

**Add a dashboard page.** Add a chart list to the `charts` dict in `pipeline.run_pipeline` and a row to `report.PAGE_META`. Empty pages are hidden automatically.

**Add an input format.** Add a loader next to `load_csv` and call it from `pipeline.load_inputs`.
