# Contributing

Thanks for helping improve AutoInsight AI.

## Set up

```bash
git clone https://github.com/YOUR_USERNAME/autoinsight-ai.git
cd autoinsight-ai
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## Making a change

1. Create a branch: `git checkout -b my-change`
2. Make your change and add or update a test in `tests/`.
3. Run `pytest` and make sure everything passes.
4. Open a pull request describing what changed and why.

## Good first contributions

- A new insight rule (see `autoinsight/insights.py` and `autoinsight/churn.py`)
- A new KPI type (see `autoinsight/kpis.py`)
- Support for Excel or Parquet input (see `autoinsight/data_loader.py`)

See `docs/ARCHITECTURE.md` for how the pieces fit together.
