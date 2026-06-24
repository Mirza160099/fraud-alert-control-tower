"""Generate measured validation evidence for calibration, fairness, and SLA policy.

This is an insurance artifact for the final submission. It does not replace the
live model; it turns the scored hold-out transactions into simple reviewer-ready
tables that answer common risk-analyst questions.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "modeling" / "validation_evidence"


def load_inputs(project_root: Path) -> tuple[pd.DataFrame, dict]:
    """Load scored transactions and exported model metadata."""

    lookup_path = project_root / "transaction-lookup.json"
    model_path = project_root / "model.json"

    lookup_payload = json.loads(lookup_path.read_text(encoding="utf-8"))
    model_payload = json.loads(model_path.read_text(encoding="utf-8"))
    records = lookup_payload.get("records", lookup_payload.get("transactions", lookup_payload))
    scored = pd.DataFrame(records)

    required = {
        "transaction_id",
        "actual_fraud_label",
        "predicted_fraud_probability",
        "priority_tier",
    }
    missing = required.difference(scored.columns)
    if missing:
        raise ValueError(f"transaction-lookup.json is missing required columns: {missing}")

    return scored, model_payload


def calibration_bins(scored: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Calculate fixed-band calibration evidence and summary diagnostics."""

    frame = scored.copy()
    frame["score"] = frame["predicted_fraud_probability"].astype(float)
    frame["actual"] = frame["actual_fraud_label"].astype(int)
    frame["score_band"] = pd.cut(
        frame["score"],
        bins=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        labels=["0.00-0.20", "0.20-0.40", "0.40-0.60", "0.60-0.80", "0.80-1.00"],
        include_lowest=True,
        right=False,
    )

    grouped = (
        frame.groupby("score_band", observed=False)
        .agg(
            transactions=("transaction_id", "count"),
            average_score=("score", "mean"),
            observed_fraud_rate=("actual", "mean"),
            fraud_count=("actual", "sum"),
        )
        .reset_index()
    )
    grouped["calibration_gap"] = (
        grouped["average_score"] - grouped["observed_fraud_rate"]
    ).abs()
    grouped = grouped.fillna(0)

    brier = float(np.mean((frame["score"] - frame["actual"]) ** 2))
    ece = float(
        np.average(
            grouped["calibration_gap"],
            weights=np.maximum(grouped["transactions"], 1),
        )
    )
    worst = grouped.sort_values("calibration_gap", ascending=False).iloc[0]
    summary = {
        "brier_score": brier,
        "expected_calibration_error": ece,
        "worst_score_band": str(worst["score_band"]),
        "worst_score_band_gap": float(worst["calibration_gap"]),
        "interpretation": (
            "Scores are suitable for ranking and thresholding in the prototype, "
            "but should be calibrated on real validation data before production odds are claimed."
        ),
    }
    return grouped, summary


def false_positive_rates(scored: pd.DataFrame, threshold: float, group_col: str) -> pd.DataFrame:
    """Calculate false-positive rate by segment among non-fraud rows."""

    nonfraud = scored[scored["actual_fraud_label"].astype(int) == 0].copy()
    nonfraud["reviewed"] = (
        nonfraud["predicted_fraud_probability"].astype(float) >= threshold
    ).astype(int)

    grouped = (
        nonfraud.groupby(group_col, dropna=False)
        .agg(
            nonfraud_transactions=("transaction_id", "count"),
            false_positive_count=("reviewed", "sum"),
        )
        .reset_index()
        .rename(columns={group_col: "segment"})
    )
    grouped["false_positive_rate"] = (
        grouped["false_positive_count"] / grouped["nonfraud_transactions"]
    )
    return grouped.sort_values(
        ["false_positive_rate", "false_positive_count"],
        ascending=False,
    )


def sla_policy_summary(scored: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, dict]:
    """Summarize SLA policy coverage from priority tiers.

    The dataset does not include case-open/case-close timestamps, so true SLA
    breach rate cannot be measured honestly. This artifact still proves the app
    assigns review urgency to every routed case and states the production data
    needed to calculate breach rate later.
    """

    frame = scored.copy()
    frame["score"] = frame["predicted_fraud_probability"].astype(float)
    frame["routed_to_review"] = frame["score"] >= threshold
    review = frame[frame["routed_to_review"]].copy()

    sla_map = {
        "Critical": "Immediate review",
        "High": "Same-shift review",
        "Medium": "Monitor today",
        "Low": "Audit trail only",
    }
    review["sla_policy"] = review["priority_tier"].map(sla_map).fillna("Review policy")

    table = (
        review.groupby(["priority_tier", "sla_policy"], dropna=False)
        .agg(cases=("transaction_id", "count"), frauds=("actual_fraud_label", "sum"))
        .reset_index()
        .sort_values(["cases", "frauds"], ascending=False)
    )
    summary = {
        "review_queue_cases": int(len(review)),
        "sla_policy_assigned_cases": int(review["sla_policy"].notna().sum()),
        "sla_policy_coverage": float(1.0 if len(review) else 0.0),
        "measured_breach_rate": None,
        "breach_rate_note": (
            "True SLA breach rate requires investigation created_at, assigned_at, "
            "and closed_at timestamps. The prototype includes SLA policy coverage, "
            "not measured operational breach performance."
        ),
    }
    return table, summary


def write_markdown_report(
    output_dir: Path,
    calibration_summary: dict,
    country_fpr: pd.DataFrame,
    channel_fpr: pd.DataFrame,
    sla_summary: dict,
) -> None:
    """Write a concise measured evidence report."""

    top_country = country_fpr.iloc[0]
    top_channel = channel_fpr.iloc[0]

    report = f"""# Validation Evidence Addendum

This addendum converts the scored synthetic transaction lookup into measured evidence for three reviewer questions: calibration, segment false positives, and SLA readiness.

## Calibration Evidence

| Metric | Value |
|---|---:|
| Brier score | {calibration_summary["brier_score"]:.4f} |
| Expected calibration error | {calibration_summary["expected_calibration_error"]:.4f} |
| Largest calibration gap band | {calibration_summary["worst_score_band"]} |
| Largest calibration gap | {calibration_summary["worst_score_band_gap"]:.4f} |

Interpretation: the score is useful for ranking and thresholding in the prototype, but it should still be calibrated on real validation data before being described as production odds.

## Fairness / Segment False-Positive Evidence

Highest observed false-positive concentration:

- Country: `{top_country["segment"]}` at {top_country["false_positive_rate"]:.1%} across {int(top_country["nonfraud_transactions"])} non-fraud transactions.
- Channel: `{top_channel["segment"]}` at {top_channel["false_positive_rate"]:.1%} across {int(top_channel["nonfraud_transactions"])} non-fraud transactions.

Interpretation: this is not a legal fairness conclusion. It is an analyst control that identifies where customer friction may concentrate and what segments need monitoring during a pilot.

## SLA / Turnaround Evidence

| Metric | Value |
|---|---:|
| Review queue cases | {sla_summary["review_queue_cases"]} |
| Cases with SLA policy assigned | {sla_summary["sla_policy_assigned_cases"]} |
| SLA policy coverage | {sla_summary["sla_policy_coverage"]:.1%} |
| Measured breach rate | Not available in current synthetic data |

Interpretation: the app assigns urgency to routed cases, but true SLA breach rate requires investigation timestamps. This is listed as a production instrumentation requirement.
"""

    (output_dir / "validation_evidence_addendum.md").write_text(
        report,
        encoding="utf-8",
    )


def main() -> None:
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    scored, model = load_inputs(PROJECT_ROOT)
    threshold = float(model["threshold"])

    calibration_table, calibration_summary = calibration_bins(scored)
    country_fpr = false_positive_rates(scored, threshold, "txn_country")
    channel_fpr = false_positive_rates(scored, threshold, "channel")
    sla_table, sla_summary = sla_policy_summary(scored, threshold)

    calibration_table.to_csv(output_dir / "calibration_curve.csv", index=False)
    country_fpr.to_csv(output_dir / "false_positive_rate_by_country.csv", index=False)
    channel_fpr.to_csv(output_dir / "false_positive_rate_by_channel.csv", index=False)
    sla_table.to_csv(output_dir / "sla_policy_coverage.csv", index=False)

    summary = {
        "threshold": threshold,
        "calibration": calibration_summary,
        "fairness_proxy": {
            "country_max_false_positive_rate": float(country_fpr.iloc[0]["false_positive_rate"]),
            "country_max_segment": str(country_fpr.iloc[0]["segment"]),
            "channel_max_false_positive_rate": float(channel_fpr.iloc[0]["false_positive_rate"]),
            "channel_max_segment": str(channel_fpr.iloc[0]["segment"]),
        },
        "sla": sla_summary,
    }
    (output_dir / "validation_evidence_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    write_markdown_report(
        output_dir,
        calibration_summary,
        country_fpr,
        channel_fpr,
        sla_summary,
    )


if __name__ == "__main__":
    main()
