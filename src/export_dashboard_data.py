"""Export Step 3 and Step 4 outputs for the static control tower app."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from fraud_pipeline import PROJECT_ROOT


DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "step_05_vercel_app" / "dashboard-data.json"
STEP_03_DIR = PROJECT_ROOT / "outputs" / "step_03_model_selection"
STEP_04_DIR = PROJECT_ROOT / "outputs" / "step_04_explainability"


def parse_args() -> argparse.Namespace:
    """Parse export destination."""

    parser = argparse.ArgumentParser(
        description="Export dashboard data for the Vercel-style app."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Destination dashboard-data.json path.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    """Read a JSON file."""

    return json.loads(path.read_text(encoding="utf-8"))


def to_records(frame: pd.DataFrame, limit: int | None = None) -> list[dict]:
    """Convert a dataframe into JSON records with optional row limiting."""

    if limit is not None:
        frame = frame.head(limit)
    return frame.to_dict("records")


def build_dashboard_payload() -> dict:
    """Build a compact payload for the app's queue and metrics tabs."""

    metrics = read_json(STEP_03_DIR / "metrics.json")
    model_comparison = pd.read_csv(STEP_03_DIR / "model_comparison.csv")
    capacity_thresholds = pd.read_csv(STEP_03_DIR / "capacity_thresholds.csv")
    champion_predictions = pd.read_csv(STEP_03_DIR / "champion_test_predictions.csv")
    case_review = pd.read_csv(STEP_04_DIR / "case_review_explanations.csv")
    feature_importance = pd.read_csv(STEP_04_DIR / "global_feature_importance.csv")

    review_queue = champion_predictions[
        champion_predictions["predicted_review_label"] == 1
    ].copy()
    queue_size = int(len(review_queue))
    frauds_in_queue = int(review_queue["actual_fraud_label"].sum())
    queue_hit_rate = frauds_in_queue / queue_size if queue_size else 0

    top_queue_cases = case_review.rename(
        columns={
            "existing_alert_generated": "alert_generated",
        }
    ).head(15)

    return {
        "metrics": metrics,
        "queue_summary": {
            "queue_size": queue_size,
            "frauds_in_queue": frauds_in_queue,
            "queue_hit_rate": queue_hit_rate,
            "missed_existing_alerts_in_top_cases": int(
                (top_queue_cases["alert_generated"] == 0).sum()
            ),
        },
        "model_comparison": to_records(
            model_comparison.sort_values(
                "test_average_precision_pr_auc",
                ascending=False,
            )
        ),
        "capacity_thresholds": to_records(capacity_thresholds),
        "top_queue_cases": to_records(top_queue_cases),
        "global_feature_importance": to_records(feature_importance),
    }


def main() -> None:
    """Write dashboard-data.json."""

    args = parse_args()
    payload = build_dashboard_payload()
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
