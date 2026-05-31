"""Step 4 explainability for the champion fraud model.

This module translates model output into investigator-friendly evidence. It
uses two complementary techniques:

1. Global permutation importance: which features matter most overall.
2. Local reference-value sensitivity: for one transaction, how much each actual
   value changes risk compared with a typical training-set value.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from fraud_pipeline import (
    PROJECT_ROOT,
    build_modeling_table,
    classify_priority,
    get_candidate_features,
    infer_column_types,
    load_raw_tables,
    select_top_features_by_mutual_info,
    split_modeling_data,
    write_json,
)


DEFAULT_STEP_04_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "step_04_explainability"


FEATURE_LABELS = {
    "geo_distance_km": "geographic distance",
    "txn_country": "transaction country",
    "synthetic_identity_score": "synthetic identity score",
    "merchant_risk_score": "transaction merchant risk score",
    "channel": "payment channel",
    "txn_hour": "transaction hour",
    "device_risk_score": "device risk score",
    "merchant_profile_risk_score": "merchant profile risk score",
    "transaction_amount_usd": "transaction amount",
    "amount_log1p": "log-scaled transaction amount",
}


def load_champion_package(champion_model_path: Path) -> dict:
    """Load the Step 3 champion model package."""

    with champion_model_path.open("rb") as model_file:
        return pickle.load(model_file)


def build_reference_profile(X_train: pd.DataFrame) -> dict[str, Any]:
    """Create typical values used for local explanation perturbations."""

    numeric_features, categorical_features = infer_column_types(X_train)
    reference_profile: dict[str, Any] = {}

    for feature in numeric_features:
        reference_profile[feature] = float(X_train[feature].median())

    for feature in categorical_features:
        mode_values = X_train[feature].mode(dropna=True)
        reference_profile[feature] = (
            str(mode_values.iloc[0]) if len(mode_values) else "__MISSING__"
        )

    return reference_profile


def predict_probability(model, row: pd.Series, selected_features: list[str]) -> float:
    """Score one transaction row with the champion model."""

    frame = pd.DataFrame([row[selected_features]], columns=selected_features)
    return float(model.predict_proba(frame)[0, 1])


def local_feature_deltas(
    model,
    row: pd.Series,
    selected_features: list[str],
    reference_profile: dict[str, Any],
) -> pd.DataFrame:
    """Measure how each actual feature value changes one transaction's risk."""

    original_probability = predict_probability(model, row, selected_features)
    rows = []

    for feature in selected_features:
        perturbed_row = row.copy()
        perturbed_row[feature] = reference_profile[feature]
        perturbed_probability = predict_probability(
            model,
            perturbed_row,
            selected_features,
        )
        risk_delta = original_probability - perturbed_probability

        rows.append(
            {
                "feature": feature,
                "actual_value": row[feature],
                "reference_value": reference_profile[feature],
                "original_probability": original_probability,
                "perturbed_probability": perturbed_probability,
                "risk_delta": risk_delta,
                "absolute_delta": abs(risk_delta),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["risk_delta", "absolute_delta"], ascending=[False, False])
        .reset_index(drop=True)
    )


def format_value(value: Any) -> str:
    """Format values for clean, readable explanation text."""

    if isinstance(value, (float, np.floating)):
        return f"{float(value):.3f}"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def plain_english_reason(
    feature: str,
    actual_value: Any,
    reference_value: Any,
    risk_delta: float,
) -> str:
    """Convert one local feature delta into investigator-facing language."""

    label = FEATURE_LABELS.get(feature, feature.replace("_", " "))
    actual_text = format_value(actual_value)
    reference_text = format_value(reference_value)
    direction = "increased" if risk_delta >= 0 else "reduced"

    return (
        f"{label} was {actual_text} compared with a typical value of "
        f"{reference_text}; this {direction} the model risk score by "
        f"{abs(risk_delta):.3f}."
    )


def build_local_explanations(
    model,
    scored_test_rows: pd.DataFrame,
    selected_features: list[str],
    reference_profile: dict[str, Any],
    threshold: float,
    sample_size: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create local reason rows and a compact case-review table."""

    highest_risk_rows = scored_test_rows.head(sample_size).copy()
    reason_rows = []
    case_rows = []

    for case_rank, (_, row) in enumerate(highest_risk_rows.iterrows(), start=1):
        deltas = local_feature_deltas(
            model,
            row,
            selected_features,
            reference_profile,
        )

        positive_deltas = deltas[deltas["risk_delta"] > 0].head(3)
        if positive_deltas.empty:
            positive_deltas = deltas.head(3)

        reasons = []

        for reason_rank, delta_row in enumerate(
            positive_deltas.itertuples(index=False),
            start=1,
        ):
            reason_text = plain_english_reason(
                delta_row.feature,
                delta_row.actual_value,
                delta_row.reference_value,
                delta_row.risk_delta,
            )
            reasons.append(reason_text)

            reason_rows.append(
                {
                    "case_rank": case_rank,
                    "transaction_id": row["transaction_id"],
                    "predicted_fraud_probability": row[
                        "predicted_fraud_probability"
                    ],
                    "priority_tier": row["priority_tier"],
                    "reason_rank": reason_rank,
                    "feature": delta_row.feature,
                    "actual_value": delta_row.actual_value,
                    "reference_value": delta_row.reference_value,
                    "risk_delta": delta_row.risk_delta,
                    "plain_english_reason": reason_text,
                }
            )

        case_rows.append(
            {
                "case_rank": case_rank,
                "transaction_id": row["transaction_id"],
                "event_ts": row["event_ts"],
                "actual_fraud_label": row["actual_fraud_label"],
                "existing_alert_generated": row["alert_generated"],
                "predicted_fraud_probability": row["predicted_fraud_probability"],
                "prediction": (
                    "Review as fraud risk"
                    if row["predicted_fraud_probability"] >= threshold
                    else "Monitor as likely legitimate"
                ),
                "priority_tier": row["priority_tier"],
                "reason_1": reasons[0] if len(reasons) > 0 else "",
                "reason_2": reasons[1] if len(reasons) > 1 else "",
                "reason_3": (
                    reasons[2]
                    if len(reasons) > 2
                    else "No additional material risk-increasing driver was detected."
                ),
            }
        )

    return pd.DataFrame(reason_rows), pd.DataFrame(case_rows)


def build_scored_test_rows(
    model,
    X_test: pd.DataFrame,
    test_context: pd.DataFrame,
    y_test: pd.Series,
    selected_features: list[str],
    threshold: float,
) -> pd.DataFrame:
    """Combine test features, context, predictions, and priority tiers."""

    probabilities = model.predict_proba(X_test[selected_features])[:, 1]

    scored_rows = test_context.copy()
    scored_rows["actual_fraud_label"] = y_test.to_numpy()
    scored_rows["predicted_fraud_probability"] = probabilities
    scored_rows["predicted_review_label"] = (probabilities >= threshold).astype(int)
    scored_rows["priority_tier"] = [
        classify_priority(probability, threshold) for probability in probabilities
    ]

    for feature in selected_features:
        scored_rows[feature] = X_test[feature].to_numpy()

    return scored_rows.sort_values(
        "predicted_fraud_probability",
        ascending=False,
    ).reset_index(drop=True)


def build_global_importance(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    selected_features: list[str],
) -> pd.DataFrame:
    """Calculate global permutation importance on the held-out test set."""

    importance = permutation_importance(
        model,
        X_test[selected_features],
        y_test,
        scoring="average_precision",
        n_repeats=20,
        random_state=42,
        n_jobs=1,
    )

    return (
        pd.DataFrame(
            {
                "feature": selected_features,
                "permutation_importance_mean_pr_auc": importance.importances_mean,
                "permutation_importance_std": importance.importances_std,
            }
        )
        .sort_values("permutation_importance_mean_pr_auc", ascending=False)
        .reset_index(drop=True)
    )


def write_step_04_report(
    output_dir: Path,
    champion_package: dict,
    global_importance: pd.DataFrame,
    case_review: pd.DataFrame,
) -> None:
    """Write the Step 4 explainability progress report."""

    importance_lines = "\n".join(
        "| {feature} | {permutation_importance_mean_pr_auc:.6f} | "
        "{permutation_importance_std:.6f} |".format(**row)
        for row in global_importance.to_dict("records")
    )

    top_cases = case_review.head(5)
    case_lines = "\n".join(
        "| {transaction_id} | {predicted_fraud_probability:.4f} | "
        "{priority_tier} | {reason_1} |".format(**row)
        for row in top_cases.to_dict("records")
    )

    report = f"""# Progress Report - Step 04: Explainability Layer

## What We Built

This step added a model-agnostic explainability layer for the Step 3 champion model.

The method has two parts:

1. Global permutation importance, which shows which features affect model performance most overall.
2. Local reference-value sensitivity, which explains an individual transaction by replacing each feature with a typical training-set value and measuring the change in fraud probability.

## Champion Model

- Model: `{champion_package["model_name"]}`
- Threshold: `{champion_package["threshold"]:.4f}`
- Capacity policy: `{champion_package["threshold_selection_method"]}`

## Global Feature Importance

Permutation importance is measured using held-out test-set PR-AUC, which is better than accuracy for rare fraud.

| Feature | Mean PR-AUC importance | Std |
|---|---:|---:|
{importance_lines}

## Example Local Explanations

| Transaction | Fraud probability | Priority | Top reason |
|---|---:|---|---|
{case_lines}

## How To Explain This In An Interview

I did not just output a black-box fraud score. I created a reviewer-facing explanation layer: global importance tells risk leadership which signals matter across the portfolio, while local sensitivity tells an investigator why a specific case moved into the queue.

## Artifacts Created

- `global_feature_importance.csv`
- `local_explanations_top_cases.csv`
- `case_review_explanations.csv`
- `reference_profile.json`
- `progress_report_step_04.md`
"""

    (output_dir / "progress_report_step_04.md").write_text(report, encoding="utf-8")


def run_explainability_pipeline(
    project_kit_dir: Path,
    champion_model_path: Path,
    output_dir: Path = DEFAULT_STEP_04_OUTPUT_DIR,
    sample_size: int = 25,
) -> dict:
    """Run Step 4 explainability end to end."""

    output_dir.mkdir(parents=True, exist_ok=True)

    champion_package = load_champion_package(champion_model_path)
    model = champion_package["model"]
    selected_features = champion_package["selected_features"]
    threshold = float(champion_package["threshold"])

    bundle = load_raw_tables(project_kit_dir)
    modeling_table = build_modeling_table(bundle)
    candidate_features = get_candidate_features(modeling_table)
    split_data = split_modeling_data(modeling_table, candidate_features)

    # Recompute the selected-feature ranking as a consistency check. The final
    # selected list still comes from the saved champion package.
    top_features = select_top_features_by_mutual_info(
        split_data.X_train,
        split_data.y_train,
        top_n=len(selected_features),
    )

    X_train = split_data.X_train[selected_features]
    X_test = split_data.X_test[selected_features]
    reference_profile = build_reference_profile(X_train)

    global_importance = build_global_importance(
        model,
        X_test,
        split_data.y_test,
        selected_features,
    )

    scored_test_rows = build_scored_test_rows(
        model,
        X_test,
        split_data.test_context,
        split_data.y_test,
        selected_features,
        threshold,
    )
    local_explanations, case_review = build_local_explanations(
        model,
        scored_test_rows,
        selected_features,
        reference_profile,
        threshold,
        sample_size,
    )

    global_importance.to_csv(
        output_dir / "global_feature_importance.csv",
        index=False,
    )
    local_explanations.to_csv(
        output_dir / "local_explanations_top_cases.csv",
        index=False,
    )
    case_review.to_csv(output_dir / "case_review_explanations.csv", index=False)
    write_json(output_dir / "reference_profile.json", reference_profile)

    metrics = {
        "champion_model_name": champion_package["model_name"],
        "threshold": threshold,
        "selected_features": selected_features,
        "top_feature_consistency_check": top_features["source_feature"].tolist(),
        "explained_case_count": int(len(case_review)),
        "top_global_feature": (
            str(global_importance.iloc[0]["feature"])
            if len(global_importance)
            else None
        ),
    }
    write_json(output_dir / "metrics.json", metrics)

    write_step_04_report(
        output_dir=output_dir,
        champion_package=champion_package,
        global_importance=global_importance,
        case_review=case_review,
    )

    return metrics
