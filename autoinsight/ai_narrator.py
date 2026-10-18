"""
ai_narrator.py
--------------
Optional layer that turns the structured, rule-based insights (insights.py)
into a polished, executive-ready narrative using the Claude API.

This is fully optional: the tool works end-to-end with pure Python/pandas
logic (see insights.py). If ANTHROPIC_API_KEY is set, this module produces a
more fluent written summary on top of that already-correct analysis --
Claude is used for communication, not for computing the numbers themselves,
which keeps every reported figure fully auditable.
"""

import os
import json


SYSTEM_PROMPT = """You are a senior data analyst writing the executive summary
section of an automated analytics report. You will be given a JSON payload of
already-computed, verified statistics and rule-based findings about a dataset.

Rules:
- Do NOT invent numbers. Only reference figures present in the payload.
- Write in clear, confident business language, not technical jargon.
- Structure your response as:
  1. A 2-3 sentence executive summary of overall data health and key story.
  2. "Key Trends" - short bullet points (use "- ") of the most important patterns.
  3. "Top Business Risks" - short bullet points of the most concerning findings.
  4. "Recommended Actions" - short bullet points, prioritized, concrete next steps.
Keep the whole response under 300 words. Plain text only, no markdown headers
other than the bold section labels shown above followed by a colon.
"""


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def generate_narrative(profile: dict, insights: list, dataset_name: str = "dataset") -> str:
    """
    Calls Claude to generate an executive narrative. Falls back to a simple
    templated summary if no API key is configured or the call fails, so the
    report generation never breaks the pipeline.
    """
    if not is_available():
        return _fallback_narrative(profile, insights)

    try:
        import anthropic
        client = anthropic.Anthropic()

        payload = {
            "dataset_name": dataset_name,
            "profile": profile,
            "findings": [
                {
                    "title": i.title,
                    "finding": i.finding,
                    "severity": i.severity,
                    "business_problem": i.business_problem,
                    "recommendation": i.recommendation,
                }
                for i in insights[:12]
            ],
        }

        response = client.messages.create(
            model=os.environ.get("AUTOINSIGHT_MODEL", "claude-sonnet-5-5"),
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload, default=str)}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    except Exception as e:
        fallback = _fallback_narrative(profile, insights)
        return fallback + f"\n\n[AI narrative unavailable, showing rule-based summary. Reason: {e}]"


def _fallback_narrative(profile: dict, insights: list) -> str:
    """Deterministic, no-API-key summary so the tool always produces output."""
    n_critical = sum(1 for i in insights if i.severity == "critical")
    n_watch = sum(1 for i in insights if i.severity == "watch")

    lines = [
        f"This dataset contains {profile['n_rows']:,} rows and {profile['n_cols']} columns, "
        f"with {profile['missing_total_pct']}% average missingness and "
        f"{profile['duplicate_rows']} duplicate rows. Automated analysis surfaced "
        f"{len(insights)} findings ({n_critical} critical, {n_watch} to watch).",
        "",
        "Key Trends:",
    ]
    for i in [x for x in insights if x.severity == "info"][:3]:
        lines.append(f"- {i.finding}")

    lines.append("")
    lines.append("Top Business Risks:")
    for i in [x for x in insights if x.severity in ("critical", "watch")][:4]:
        lines.append(f"- {i.finding}")

    lines.append("")
    lines.append("Recommended Actions:")
    for i in insights[:4]:
        lines.append(f"- {i.recommendation}")

    return "\n".join(lines)
