"""
data_loader.py
--------------
Generic, schema-agnostic CSV loader. Works on ANY dataset by:
  1. Reading the raw CSV
  2. Attempting to auto-detect date/datetime columns
  3. Classifying every column into one of: numeric, categorical, datetime, identifier/text
This classification drives every downstream module (EDA, insights, charts).
"""

import re
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore", message="Could not infer format")


_ID_STEMS = {"customer", "user", "order", "client", "account", "member", "patient", "employee",
             "product", "transaction", "row", "record", "item", "session", "invoice"}


def _has_id_token(name: str) -> bool:
    """True for names like id, customer_id, CustomerID, userId -- but not 'paid' or 'width'."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(name))
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", spaced.lower()) if t]
    lower = str(name).lower()
    return ("id" in tokens or "uuid" in tokens
            or (lower.endswith("id") and lower[:-2] in _ID_STEMS))


def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV file robustly, handling common encoding issues."""
    for encoding in ("utf-8", "latin1", "cp1252"):
        try:
            df = pd.read_csv(path, encoding=encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        raise ValueError(f"Could not read {path} with common encodings.")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def _try_parse_dates(series: pd.Series) -> bool:
    """Return True if a column looks like a date/datetime column."""
    is_textlike = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
    if is_textlike or "datetime" in str(series.dtype):
        sample = series.dropna().astype(str).head(20)
        if sample.empty:
            return False
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                parsed = pd.to_datetime(sample, errors="coerce")
            return parsed.notna().mean() > 0.8
        except Exception:
            return False
    return False


def classify_columns(df: pd.DataFrame) -> dict:
    """
    Classify each column into: numeric, categorical, datetime, identifier.

    Rules of thumb (kept simple & transparent so results are explainable):
      - datetime: parses as a date for >80% of non-null sample values
      - numeric: pandas numeric dtype
      - identifier: object/int column where >90% of values are unique
                    (e.g. IDs, emails, names) -> excluded from most stats/charts
      - categorical: everything else (low/medium cardinality text)
    """
    numeric_cols, categorical_cols, datetime_cols, identifier_cols = [], [], [], []
    n = len(df)

    for col in df.columns:
        series = df[col]

        if _try_parse_dates(series):
            df[col] = pd.to_datetime(series, errors="coerce")
            datetime_cols.append(col)
            continue

        if pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            n_unique = non_null.nunique()
            mostly_unique = n > 0 and n_unique / n > 0.95
            integer_valued = len(non_null) > 0 and bool((non_null % 1 == 0).all())
            # IDs: unique-ish values with an id-like name, or a running row index (1,2,3...)
            if mostly_unique and _has_id_token(col):
                identifier_cols.append(col)
            elif integer_valued and n_unique / max(n, 1) > 0.99 and non_null.is_monotonic_increasing:
                identifier_cols.append(col)
            elif n_unique <= 2:
                # 0/1 flags (HasCard, IsActive...) behave like categories, not measurements
                categorical_cols.append(col)
            else:
                numeric_cols.append(col)
            continue

        # Object/text column
        n_unique = series.nunique(dropna=True)
        nunique_ratio = n_unique / n if n else 0
        # near-unique text (ids, emails) or high-cardinality text (surnames, free text)
        if nunique_ratio > 0.9 or (n_unique > 50 and nunique_ratio > 0.2):
            identifier_cols.append(col)
        else:
            categorical_cols.append(col)

    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "datetime": datetime_cols,
        "identifier": identifier_cols,
    }


def profile_dataset(df: pd.DataFrame) -> dict:
    """High-level shape / quality profile used at the top of the report."""
    return {
        "n_rows": len(df),
        "n_cols": df.shape[1],
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_total_pct": round(df.isna().mean().mean() * 100, 2),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1_000_000, 2),
    }
