"""Export transaction-level lookup data for the static fraud app.

The Vercel app runs without a Python backend, so any transaction search data
has to be exported into a browser-readable JSON file. This script joins the raw
synthetic transaction, customer, and merchant tables, scores the transactions
with the saved champion model, creates local explanation text, and writes a
compact lookup file for the frontend.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from fraud_pipeline import DatasetBundle, build_modeling_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = (
    PROJECT_ROOT.parents[1]
    / "REAL_SUBMISSION_FINAL_2026-06-02"
    / "data"
    / "raw"
)
DEFAULT_MODEL_PATH = (
    PROJECT_ROOT.parents[1]
    / "outputs"
    / "step_03_model_selection"
    / "champion_model.pkl"
)
DEFAULT_REFERENCE_PROFILE_PATH = (
    PROJECT_ROOT.parents[1]
    / "outputs"
    / "step_04_explainability"
    / "reference_profile.json"
)
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "transaction-lookup.json"

FEATURE_LABELS = {
    "geo_distance_km": "geographic distance",
    "txn_country": "transaction country",
    "synthetic_identity_score": "synthetic identity score",
    "merchant_risk_score": "merchant risk score",
    "channel": "payment channel",
    "txn_hour": "transaction hour",
    "device_risk_score": "device risk score",
    "merchant_profile_risk_score": "merchant profile risk score",
    "transaction_amount_usd": "transaction amount",
    "amount_log1p": "log-scaled transaction amount",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI paths for reproducible lookup export."""

    parser = argparse.ArgumentParser(
        description="Export full transaction lookup data for the static web app."
    )
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument(
        "--reference-profile-path",
        type=Path,
        default=DEFAULT_REFERENCE_PROFILE_PATH,
    )
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def priority_from_probability(probability: float, threshold: float) -> tuple[str, str]:
    """Convert a fraud probability into the same tiers used by the frontend."""

    if probability >= max(0.82, threshold):
        return "Critical", "Immediate review"
    if probability >= threshold:
        return "High", "Review as fraud risk"
    if probability >= 0.35:
        return "Medium", "Monitor closely"
    return "Low", "Likely legitimate"


def format_value(value) -> str:
    """Format numbers and categories for explanation sentences."""

    if isinstance(value, (float, np.floating)):
        return f"{float(value):.3f}"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def json_number(value, digits: int | None = None):
    """Return a JSON-safe number, or None when the value is missing."""

    number = float(value)
    if not np.isfinite(number):
        return None
    if digits is not None:
        return round(number, digits)
    return number


def explanation_sentence(feature: str, actual, reference, delta: float) -> str:
    """Write readable local-sensitivity explanation text."""

    label = FEATURE_LABELS.get(feature, feature)
    direction = "increased" if delta >= 0 else "reduced"
    return (
        f"{label} was {format_value(actual)} compared with a typical value of "
        f"{format_value(reference)}; this {direction} the model risk score by "
        f"{abs(delta):.3f}."
    )


def local_reasons(row: pd.Series, model, selected_features: list[str], reference: dict) -> list[str]:
    """Compute simple local sensitivity reasons for one transaction."""

    original = row[selected_features].to_frame().T
    original_probability = float(model.predict_proba(original)[0, 1])
    impacts: list[tuple[float, str]] = []

    for feature in selected_features:
        changed = original.copy()
        changed.loc[:, feature] = reference.get(feature, changed.iloc[0][feature])
        if feature == "transaction_amount_usd" and "amount_log1p" in selected_features:
            changed.loc[:, "amount_log1p"] = np.log1p(
                max(0.0, float(reference.get("transaction_amount_usd", 0.0)))
            )
        changed_probability = float(model.predict_proba(changed)[0, 1])
        delta = original_probability - changed_probability
        if abs(delta) >= 0.001:
            impacts.append(
                (
                    abs(delta),
                    explanation_sentence(
                        feature,
                        row[feature],
                        reference.get(feature),
                        delta,
                    ),
                )
            )

    impacts.sort(key=lambda item: item[0], reverse=True)
    return [sentence for _, sentence in impacts[:3]]


def load_modeling_table(raw_dir: Path) -> pd.DataFrame:
    """Load raw CSVs and rebuild the same modeling table used for training."""

    transactions = pd.read_csv(raw_dir / "transactions.csv", parse_dates=["event_ts"])
    customers = pd.read_csv(raw_dir / "customers.csv")
    merchants = pd.read_csv(raw_dir / "merchants.csv")
    return build_modeling_table(
        DatasetBundle(
            transactions=transactions,
            customers=customers,
            merchants=merchants,
        )
    )


def main() -> None:
    """Generate transaction-lookup.json for the web app."""

    args = parse_args()
    modeling_table = load_modeling_table(args.raw_dir)

    with args.model_path.open("rb") as model_file:
        champion_package = pickle.load(model_file)
    model = champion_package["model"]
    selected_features = champion_package["selected_features"]
    threshold = float(champion_package["threshold"])
    reference_profile = json.loads(
        args.reference_profile_path.read_text(encoding="utf-8")
    )

    probabilities = model.predict_proba(modeling_table[selected_features])[:, 1]
    export_rows = []

    for index, row in enumerate(modeling_table.itertuples(index=False)):
        probability = float(probabilities[index])
        tier, action = priority_from_probability(probability, threshold)

        export_rows.append(
            {
                "transaction_id": row.transaction_id,
                "event_ts": row.event_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "actual_fraud_label": int(row.fraud_label),
                "alert_generated": int(row.alert_generated),
                "predicted_fraud_probability": probability,
                "prediction": action,
                "priority_tier": tier,
                "transaction_amount_usd": json_number(row.transaction_amount_usd, 2),
                "txn_country": row.txn_country,
                "channel": row.channel,
                "txn_hour": None
                if not np.isfinite(float(row.txn_hour))
                else int(row.txn_hour),
                "geo_distance_km": json_number(row.geo_distance_km, 3),
                "device_risk_score": json_number(row.device_risk_score, 3),
                "synthetic_identity_score": json_number(
                    row.synthetic_identity_score, 3
                ),
                "merchant_risk_score": json_number(row.merchant_risk_score, 3),
                "merchant_profile_risk_score": json_number(
                    row.merchant_profile_risk_score, 3
                ),
            }
        )

    export_rows.sort(
        key=lambda item: (-item["predicted_fraud_probability"], item["transaction_id"])
    )
    payload = {
        "source": "raw synthetic transactions scored with saved champion model",
        "record_count": len(export_rows),
        "records": export_rows,
    }

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(
        json.dumps(payload, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(export_rows):,} transaction lookup records to {args.output_path}")


if __name__ == "__main__":
    main()
