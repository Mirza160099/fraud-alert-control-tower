"""Step 3 model comparison and investigator-capacity threshold tuning.

The goal of this module is not to chase a vanity accuracy number. Fraud teams
operate with limited investigator time, so this step compares stronger models
and evaluates them under realistic queue-size constraints.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    AdaBoostClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from fraud_pipeline import (
    PROJECT_ROOT,
    add_merchant_category_target_encoding,
    build_baseline_model,
    build_feature_schema,
    build_modeling_table,
    choose_threshold,
    classification_metrics,
    get_candidate_features,
    load_raw_tables,
    make_preprocessor,
    select_top_features_by_mutual_info,
    split_modeling_data,
    write_json,
)


DEFAULT_STEP_03_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "step_03_model_selection"

# These represent different operating choices for fraud leadership. A 5% queue
# means only 50 of every 1,000 transactions are routed to review.
CAPACITY_RATES = [0.01, 0.02, 0.05, 0.10, 0.15]


@dataclass(frozen=True)
class ModelCandidate:
    """Configuration for one model being compared."""

    name: str
    estimator: object
    use_sample_weight: bool = False


@dataclass(frozen=True)
class FittedCandidate:
    """A trained model plus its validation and test probabilities."""

    name: str
    pipeline: Pipeline
    validation_probabilities: np.ndarray
    test_probabilities: np.ndarray


def build_depth2_adaboost() -> AdaBoostClassifier:
    """Create a less jumpy AdaBoost model using shallow trees, not stumps."""

    base_tree = DecisionTreeClassifier(
        max_depth=2,
        min_samples_leaf=20,
        random_state=42,
    )

    try:
        return AdaBoostClassifier(
            estimator=base_tree,
            n_estimators=300,
            learning_rate=0.03,
            random_state=42,
        )
    except TypeError:
        return AdaBoostClassifier(
            base_estimator=base_tree,
            n_estimators=300,
            learning_rate=0.03,
            random_state=42,
        )


def get_model_candidates() -> list[ModelCandidate]:
    """Create the models we want to compare in Step 3."""

    return [
        ModelCandidate(
            name="logistic_regression_balanced",
            estimator=LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                solver="lbfgs",
                random_state=42,
            ),
        ),
        ModelCandidate(
            name="random_forest_balanced",
            estimator=RandomForestClassifier(
                n_estimators=500,
                max_depth=6,
                min_samples_leaf=10,
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=1,
            ),
        ),
        ModelCandidate(
            name="extra_trees_balanced",
            estimator=ExtraTreesClassifier(
                n_estimators=500,
                max_depth=6,
                min_samples_leaf=10,
                class_weight="balanced",
                random_state=42,
                n_jobs=1,
            ),
        ),
        ModelCandidate(
            name="gradient_boosting_weighted",
            estimator=GradientBoostingClassifier(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=2,
                min_samples_leaf=20,
                random_state=42,
            ),
            use_sample_weight=True,
        ),
        ModelCandidate(
            name="adaboost_depth2_weighted",
            estimator=build_depth2_adaboost(),
            use_sample_weight=True,
        ),
        ModelCandidate(
            name="adaboost_weighted",
            estimator=AdaBoostClassifier(
                n_estimators=200,
                learning_rate=0.05,
                random_state=42,
            ),
            use_sample_weight=True,
        ),
    ]


def balanced_sample_weight(y: pd.Series) -> np.ndarray:
    """Return inverse-frequency sample weights for rare-fraud training."""

    class_counts = y.value_counts()
    total_rows = len(y)
    class_weights = {
        class_label: total_rows / (len(class_counts) * count)
        for class_label, count in class_counts.items()
    }

    return y.map(class_weights).to_numpy()


def build_candidate_pipeline(
    X_train: pd.DataFrame,
    candidate: ModelCandidate,
) -> Pipeline:
    """Create a preprocessing-plus-model pipeline for one candidate."""

    return Pipeline(
        steps=[
            ("preprocessor", make_preprocessor(X_train)),
            ("classifier", candidate.estimator),
        ]
    )


def fit_candidate(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_validation: pd.DataFrame,
    X_test: pd.DataFrame,
    candidate: ModelCandidate,
) -> FittedCandidate:
    """Train one candidate and score validation/test rows."""

    pipeline = build_candidate_pipeline(X_train, candidate)

    # Some algorithms accept class_weight directly. Boosting algorithms here use
    # sample_weight so rare fraud cases still influence the fitted model.
    if candidate.use_sample_weight:
        pipeline.fit(
            X_train,
            y_train,
            classifier__sample_weight=balanced_sample_weight(y_train),
        )
    else:
        pipeline.fit(X_train, y_train)

    validation_probabilities = pipeline.predict_proba(X_validation)[:, 1]
    test_probabilities = pipeline.predict_proba(X_test)[:, 1]

    return FittedCandidate(
        name=candidate.name,
        pipeline=pipeline,
        validation_probabilities=validation_probabilities,
        test_probabilities=test_probabilities,
    )


def fit_all_candidates(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_validation: pd.DataFrame,
    X_test: pd.DataFrame,
) -> list[FittedCandidate]:
    """Fit every model candidate on the same feature set."""

    return [
        fit_candidate(
            X_train,
            y_train,
            X_validation,
            X_test,
            candidate,
        )
        for candidate in get_model_candidates()
    ]


def model_aware_feature_importance(
    fitted: FittedCandidate,
    X_validation: pd.DataFrame,
    y_validation: pd.Series,
) -> pd.DataFrame:
    """Use validation permutation importance to confirm retained features."""

    importance = permutation_importance(
        fitted.pipeline,
        X_validation,
        y_validation,
        scoring="average_precision",
        n_repeats=20,
        random_state=42,
        n_jobs=1,
    )

    return (
        pd.DataFrame(
            {
                "feature": X_validation.columns,
                "permutation_importance_mean_pr_auc": importance.importances_mean,
                "permutation_importance_std": importance.importances_std,
            }
        )
        .sort_values("permutation_importance_mean_pr_auc", ascending=False)
        .reset_index(drop=True)
    )


def prune_features_by_model_importance(
    importance: pd.DataFrame,
    minimum_features: int = 4,
) -> list[str]:
    """Keep model-aware positive features while avoiding an unstable tiny set."""

    positive = importance[
        importance["permutation_importance_mean_pr_auc"] > 0
    ]["feature"].tolist()

    if len(positive) >= minimum_features:
        return positive

    # If the validation signal is sparse, keep the least harmful top features so
    # the model remains usable, but this branch is reported in the artifact.
    return importance.head(minimum_features)["feature"].tolist()


def metrics_from_labels(
    y_true: pd.Series,
    predicted_labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict:
    """Calculate metrics when labels are already chosen by a queue policy."""

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predicted_labels,
        labels=[0, 1],
    ).ravel()
    review_count = int(predicted_labels.sum())
    total_frauds = int(y_true.sum())

    return {
        "threshold": float(threshold),
        "review_count": review_count,
        "queue_rate": float(review_count / len(y_true)),
        "accuracy": float(accuracy_score(y_true, predicted_labels)),
        "precision_hit_rate": float(
            precision_score(y_true, predicted_labels, zero_division=0)
        ),
        "recall_fraud_capture_rate": float(
            recall_score(y_true, predicted_labels, zero_division=0)
        ),
        "f1": float(f1_score(y_true, predicted_labels, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "average_precision_pr_auc": float(
            average_precision_score(y_true, probabilities)
        ),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "frauds_in_queue": int(tp),
        "total_frauds": total_frauds,
    }


def top_k_threshold_and_labels(
    probabilities: np.ndarray,
    capacity_rate: float,
) -> tuple[float, np.ndarray]:
    """Select the highest-risk transactions that fit a fixed review capacity."""

    row_count = len(probabilities)
    review_count = max(1, int(np.ceil(row_count * capacity_rate)))

    # Stable sorting makes the result deterministic when probabilities tie.
    ranked_indexes = np.argsort(-probabilities, kind="mergesort")
    selected_indexes = ranked_indexes[:review_count]

    predicted_labels = np.zeros(row_count, dtype=int)
    predicted_labels[selected_indexes] = 1

    threshold = float(probabilities[ranked_indexes[review_count - 1]])

    return threshold, predicted_labels


def labels_from_threshold(
    probabilities: np.ndarray,
    threshold: float,
) -> np.ndarray:
    """Apply a probability threshold to produce binary review labels."""

    return (probabilities >= threshold).astype(int)


def build_model_comparison_rows(
    fitted_candidates: list[FittedCandidate],
    y_validation: pd.Series,
    y_test: pd.Series,
) -> list[dict]:
    """Evaluate each model using its validation-best F1 threshold."""

    rows = []

    for fitted in fitted_candidates:
        threshold_info = choose_threshold(
            y_validation,
            fitted.validation_probabilities,
        )
        threshold = threshold_info["threshold"]
        test_metrics = classification_metrics(
            y_test,
            fitted.test_probabilities,
            threshold,
        )

        rows.append(
            {
                "model_name": fitted.name,
                "validation_best_f1_threshold": threshold,
                "validation_precision": threshold_info["precision"],
                "validation_recall": threshold_info["recall"],
                "validation_f1": threshold_info["f1"],
                "validation_roc_auc": float(
                    roc_auc_score(y_validation, fitted.validation_probabilities)
                ),
                "validation_average_precision_pr_auc": float(
                    average_precision_score(
                        y_validation,
                        fitted.validation_probabilities,
                    )
                ),
                "test_precision": test_metrics["precision"],
                "test_recall": test_metrics["recall"],
                "test_f1": test_metrics["f1"],
                "test_roc_auc": test_metrics["roc_auc"],
                "test_average_precision_pr_auc": test_metrics[
                    "average_precision_pr_auc"
                ],
                "test_review_count": (
                    test_metrics["false_positives"] + test_metrics["true_positives"]
                ),
                "test_true_positives": test_metrics["true_positives"],
                "test_false_positives": test_metrics["false_positives"],
                "test_false_negatives": test_metrics["false_negatives"],
            }
        )

    return rows


def build_capacity_rows(
    fitted_candidates: list[FittedCandidate],
    y_validation: pd.Series,
    y_test: pd.Series,
    capacity_rates: list[float],
) -> list[dict]:
    """Evaluate each model under fixed investigator queue sizes."""

    rows = []

    for fitted in fitted_candidates:
        for capacity_rate in capacity_rates:
            validation_threshold, validation_labels = top_k_threshold_and_labels(
                fitted.validation_probabilities,
                capacity_rate,
            )
            validation_metrics = metrics_from_labels(
                y_validation,
                validation_labels,
                fitted.validation_probabilities,
                validation_threshold,
            )

            # In production, the threshold is chosen before future labels are
            # known. So for test evaluation we apply the validation threshold to
            # test probabilities and then observe the resulting queue size.
            test_labels = labels_from_threshold(
                fitted.test_probabilities,
                validation_threshold,
            )
            test_metrics = metrics_from_labels(
                y_test,
                test_labels,
                fitted.test_probabilities,
                validation_threshold,
            )
            test_exact_threshold, test_exact_labels = top_k_threshold_and_labels(
                fitted.test_probabilities,
                capacity_rate,
            )
            test_exact_metrics = metrics_from_labels(
                y_test,
                test_exact_labels,
                fitted.test_probabilities,
                test_exact_threshold,
            )

            rows.append(
                {
                    "model_name": fitted.name,
                    "target_capacity_rate": capacity_rate,
                    "validation_threshold": validation_threshold,
                    "validation_review_count": validation_metrics["review_count"],
                    "validation_queue_rate": validation_metrics["queue_rate"],
                    "validation_precision_hit_rate": validation_metrics[
                        "precision_hit_rate"
                    ],
                    "validation_recall_fraud_capture_rate": validation_metrics[
                        "recall_fraud_capture_rate"
                    ],
                    "validation_f1": validation_metrics["f1"],
                    "test_review_count": test_metrics["review_count"],
                    "test_queue_rate": test_metrics["queue_rate"],
                    "test_precision_hit_rate": test_metrics["precision_hit_rate"],
                    "test_recall_fraud_capture_rate": test_metrics[
                        "recall_fraud_capture_rate"
                    ],
                    "test_f1": test_metrics["f1"],
                    "test_true_positives": test_metrics["true_positives"],
                    "test_false_positives": test_metrics["false_positives"],
                    "test_false_negatives": test_metrics["false_negatives"],
                    "test_exact_topk_threshold": test_exact_threshold,
                    "test_exact_topk_review_count": test_exact_metrics[
                        "review_count"
                    ],
                    "test_exact_topk_precision_hit_rate": test_exact_metrics[
                        "precision_hit_rate"
                    ],
                    "test_exact_topk_recall_fraud_capture_rate": test_exact_metrics[
                        "recall_fraud_capture_rate"
                    ],
                    "test_exact_topk_f1": test_exact_metrics["f1"],
                    "test_exact_topk_true_positives": test_exact_metrics[
                        "true_positives"
                    ],
                    "test_exact_topk_false_positives": test_exact_metrics[
                        "false_positives"
                    ],
                }
            )

    return rows


def choose_champion_from_capacity(
    capacity_results: pd.DataFrame,
    model_comparison: pd.DataFrame,
    target_capacity_rate: float,
) -> pd.Series:
    """Choose the champion model at the selected investigator capacity."""

    target_rows = capacity_results[
        capacity_results["target_capacity_rate"] == target_capacity_rate
    ].copy()

    if target_rows.empty:
        raise ValueError(
            f"No capacity rows found for target rate {target_capacity_rate}."
        )

    target_rows = target_rows.merge(
        model_comparison[
            [
                "model_name",
                "validation_average_precision_pr_auc",
                "validation_roc_auc",
            ]
        ],
        on="model_name",
        how="left",
    )

    # Capacity F1 is the primary operating metric because this project is an
    # investigator queue, not a pure probability-ranking exercise. PR-AUC stays
    # as a tie-breaker so we do not ignore overall rare-fraud ranking quality.
    target_rows = target_rows.sort_values(
        [
            "validation_f1",
            "validation_recall_fraud_capture_rate",
            "validation_precision_hit_rate",
            "validation_average_precision_pr_auc",
        ],
        ascending=False,
    )

    return target_rows.iloc[0]


def build_champion_prediction_table(
    test_context: pd.DataFrame,
    probabilities: np.ndarray,
    threshold: float,
    y_test: pd.Series,
) -> pd.DataFrame:
    """Create a compact champion score table for review."""

    predicted_labels = labels_from_threshold(probabilities, threshold)

    predictions = test_context.copy()
    predictions["actual_fraud_label"] = y_test.to_numpy()
    predictions["predicted_fraud_probability"] = probabilities
    predictions["predicted_review_label"] = predicted_labels

    return predictions.sort_values(
        "predicted_fraud_probability",
        ascending=False,
    )


def write_step_03_report(
    output_dir: Path,
    selected_features: list[str],
    model_comparison: pd.DataFrame,
    capacity_results: pd.DataFrame,
    champion_row: pd.Series,
    existing_alert_metrics: dict,
) -> None:
    """Write the Step 3 model-selection progress report."""

    model_table = model_comparison.sort_values(
        "validation_average_precision_pr_auc",
        ascending=False,
    )[
        [
            "model_name",
            "validation_average_precision_pr_auc",
            "test_precision",
            "test_recall",
            "test_f1",
            "test_roc_auc",
            "test_average_precision_pr_auc",
            "test_review_count",
        ]
    ]

    model_lines = "\n".join(
        "| {model_name} | {validation_average_precision_pr_auc:.4f} | "
        "{test_precision:.4f} | {test_recall:.4f} | "
        "{test_f1:.4f} | {test_roc_auc:.4f} | "
        "{test_average_precision_pr_auc:.4f} | {test_review_count} |".format(
            **row
        )
        for row in model_table.to_dict("records")
    )

    target_capacity = champion_row["target_capacity_rate"]
    target_rows = capacity_results[
        capacity_results["target_capacity_rate"] == target_capacity
    ].merge(
        model_comparison[
            [
                "model_name",
                "validation_average_precision_pr_auc",
            ]
        ],
        on="model_name",
        how="left",
    ).sort_values(
        [
            "validation_average_precision_pr_auc",
            "validation_f1",
        ],
        ascending=False,
    )
    capacity_lines = "\n".join(
        "| {model_name} | {validation_average_precision_pr_auc:.4f} | "
        "{validation_threshold:.4f} | "
        "{validation_precision_hit_rate:.4f} | "
        "{validation_recall_fraud_capture_rate:.4f} | "
        "{validation_f1:.4f} | {test_review_count} | "
        "{test_precision_hit_rate:.4f} | "
        "{test_recall_fraud_capture_rate:.4f} | "
        "{test_exact_topk_precision_hit_rate:.4f} | "
        "{test_exact_topk_recall_fraud_capture_rate:.4f} |".format(**row)
        for row in target_rows.to_dict("records")
    )

    report = f"""# Progress Report - Step 03: Model Comparison and Capacity Thresholding

## What We Built

This step compared stronger models and converted fraud probabilities into investigator-capacity thresholds. The model is now evaluated as a queue prioritization system, not only as a classifier.

## Features Used

We kept the Step 2 top-10 feature constraint so the final app remains explainable and input-friendly:

{chr(10).join(f"- `{feature}`" for feature in selected_features)}

## Models Compared

| Model | Validation PR-AUC | Test precision | Test recall | Test F1 | Test ROC-AUC | Test PR-AUC | Test reviews |
|---|---:|---:|---:|---:|---:|---:|---:|
{model_lines}

## Capacity Tuning at {target_capacity:.0%} Review Capacity

The primary operating assumption is that investigators can review about {target_capacity:.0%} of transactions. Thresholds are chosen on validation data and then applied to the held-out test set. The last two columns also show an exact top-K queue policy, where the team simply reviews the highest-risk {target_capacity:.0%} of test transactions.

| Model | Validation PR-AUC | Validation threshold | Validation hit rate | Validation fraud capture | Validation F1 | Test reviews | Test hit rate | Test fraud capture | Exact top-K hit rate | Exact top-K fraud capture |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{capacity_lines}

## Champion Choice

- Champion model: `{champion_row["model_name"]}`
- Selected operating threshold: `{champion_row["validation_threshold"]:.4f}`
- Target capacity: `{target_capacity:.0%}`
- Test review count after applying threshold: `{int(champion_row["test_review_count"])}`
- Test hit rate: `{champion_row["test_precision_hit_rate"]:.4f}`
- Test fraud capture: `{champion_row["test_recall_fraud_capture_rate"]:.4f}`
- Test F1: `{champion_row["test_f1"]:.4f}`
- Exact top-K test hit rate: `{champion_row["test_exact_topk_precision_hit_rate"]:.4f}`
- Exact top-K test fraud capture: `{champion_row["test_exact_topk_recall_fraud_capture_rate"]:.4f}`

## Existing Alert Benchmark

On the same test split, the existing `alert_generated` rule had:

- Precision / hit rate: `{existing_alert_metrics["precision"]:.4f}`
- Recall / fraud capture: `{existing_alert_metrics["recall"]:.4f}`
- F1: `{existing_alert_metrics["f1"]:.4f}`
- True positives: `{existing_alert_metrics["true_positives"]}`
- False positives: `{existing_alert_metrics["false_positives"]}`
- False negatives: `{existing_alert_metrics["false_negatives"]}`

## Interview Talking Point

This is the fraud-operations story: a model can be tuned for different staffing levels. If leadership wants a smaller queue, we can raise the threshold and improve hit rate. If leadership wants to catch more fraud, we can lower the threshold and accept more false positives. That threshold discipline is exactly what turns a data science model into an operational control.

## Artifacts Created

- `model_comparison.csv`
- `capacity_thresholds.csv`
- `champion_test_predictions.csv`
- `champion_model.pkl`
- `metrics.json`
"""

    (output_dir / "progress_report_step_03.md").write_text(report, encoding="utf-8")


def run_model_selection_pipeline(
    project_kit_dir: Path,
    output_dir: Path = DEFAULT_STEP_03_OUTPUT_DIR,
    top_n: int = 10,
    target_capacity_rate: float = 0.05,
) -> dict:
    """Run the complete Step 3 model comparison workflow."""

    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_raw_tables(project_kit_dir)
    modeling_table = build_modeling_table(bundle)
    candidate_features = get_candidate_features(modeling_table)
    split_data = split_modeling_data(modeling_table, candidate_features)
    split_data, target_encoding = add_merchant_category_target_encoding(split_data)

    top_features = select_top_features_by_mutual_info(
        split_data.X_train,
        split_data.y_train,
        top_n=top_n,
    )
    initial_selected_features = top_features["source_feature"].tolist()

    initial_X_train = split_data.X_train[initial_selected_features]
    initial_X_validation = split_data.X_validation[initial_selected_features]
    initial_X_test = split_data.X_test[initial_selected_features]

    initial_fitted_candidates = fit_all_candidates(
        initial_X_train,
        split_data.y_train,
        initial_X_validation,
        initial_X_test,
    )

    initial_model_comparison = pd.DataFrame(
        build_model_comparison_rows(
            initial_fitted_candidates,
            split_data.y_validation,
            split_data.y_test,
        )
    ).sort_values("test_average_precision_pr_auc", ascending=False)

    initial_capacity_results = pd.DataFrame(
        build_capacity_rows(
            initial_fitted_candidates,
            split_data.y_validation,
            split_data.y_test,
            CAPACITY_RATES,
        )
    )

    initial_champion_row = choose_champion_from_capacity(
        initial_capacity_results,
        initial_model_comparison,
        target_capacity_rate,
    )
    initial_champion = next(
        fitted
        for fitted in initial_fitted_candidates
        if fitted.name == initial_champion_row["model_name"]
    )

    validation_importance = model_aware_feature_importance(
        initial_champion,
        initial_X_validation,
        split_data.y_validation,
    )
    selected_features = prune_features_by_model_importance(validation_importance)
    dropped_features = [
        feature
        for feature in initial_selected_features
        if feature not in selected_features
    ]

    X_train = split_data.X_train[selected_features]
    X_validation = split_data.X_validation[selected_features]
    X_test = split_data.X_test[selected_features]

    fitted_candidates = fit_all_candidates(
        X_train,
        split_data.y_train,
        X_validation,
        X_test,
    )

    model_comparison = pd.DataFrame(
        build_model_comparison_rows(
            fitted_candidates,
            split_data.y_validation,
            split_data.y_test,
        )
    ).sort_values("test_average_precision_pr_auc", ascending=False)

    capacity_results = pd.DataFrame(
        build_capacity_rows(
            fitted_candidates,
            split_data.y_validation,
            split_data.y_test,
            CAPACITY_RATES,
        )
    )

    champion_row = choose_champion_from_capacity(
        capacity_results,
        model_comparison,
        target_capacity_rate,
    )
    champion_name = champion_row["model_name"]
    champion = next(
        fitted for fitted in fitted_candidates if fitted.name == champion_name
    )
    champion_threshold = float(champion_row["validation_threshold"])

    existing_alert_metrics = classification_metrics(
        split_data.y_test,
        split_data.test_context["alert_generated"].astype(int).to_numpy(),
        threshold=0.5,
    )

    feature_schema = build_feature_schema(split_data.X_train, selected_features)
    champion_predictions = build_champion_prediction_table(
        split_data.test_context,
        champion.test_probabilities,
        champion_threshold,
        split_data.y_test,
    )

    metrics = {
        "target_capacity_rate": float(target_capacity_rate),
        "initial_selected_features": initial_selected_features,
        "dropped_features_after_validation_importance": dropped_features,
        "selected_features": selected_features,
        "target_encoding": {
            key: value
            for key, value in target_encoding.items()
            if key != "mapping"
        },
        "champion": {
            "model_name": champion_name,
            "threshold": champion_threshold,
            "test_review_count": int(champion_row["test_review_count"]),
            "test_queue_rate": float(champion_row["test_queue_rate"]),
            "test_precision_hit_rate": float(
                champion_row["test_precision_hit_rate"]
            ),
            "test_recall_fraud_capture_rate": float(
                champion_row["test_recall_fraud_capture_rate"]
            ),
            "test_f1": float(champion_row["test_f1"]),
            "test_true_positives": int(champion_row["test_true_positives"]),
            "test_false_positives": int(champion_row["test_false_positives"]),
            "test_false_negatives": int(champion_row["test_false_negatives"]),
            "test_exact_topk_review_count": int(
                champion_row["test_exact_topk_review_count"]
            ),
            "test_exact_topk_precision_hit_rate": float(
                champion_row["test_exact_topk_precision_hit_rate"]
            ),
            "test_exact_topk_recall_fraud_capture_rate": float(
                champion_row["test_exact_topk_recall_fraud_capture_rate"]
            ),
            "test_exact_topk_f1": float(champion_row["test_exact_topk_f1"]),
            "test_exact_topk_true_positives": int(
                champion_row["test_exact_topk_true_positives"]
            ),
            "test_exact_topk_false_positives": int(
                champion_row["test_exact_topk_false_positives"]
            ),
        },
        "existing_alert_benchmark": existing_alert_metrics,
    }

    champion_package = {
        "model": champion.pipeline,
        "model_name": champion_name,
        "selected_features": selected_features,
        "initial_selected_features": initial_selected_features,
        "dropped_features_after_validation_importance": dropped_features,
        "threshold": champion_threshold,
        "target_capacity_rate": target_capacity_rate,
        "feature_schema": feature_schema,
        "target_encoding": target_encoding,
        "feature_selection_method": (
            "training-only mutual information filter plus validation "
            "permutation-importance pruning"
        ),
        "threshold_selection_method": "validation_top_k_capacity",
    }

    top_features.to_csv(output_dir / "initial_mutual_information_features.csv", index=False)
    validation_importance.to_csv(
        output_dir / "validation_permutation_importance.csv",
        index=False,
    )
    model_comparison.to_csv(output_dir / "model_comparison.csv", index=False)
    capacity_results.to_csv(output_dir / "capacity_thresholds.csv", index=False)
    champion_predictions.to_csv(
        output_dir / "champion_test_predictions.csv",
        index=False,
    )
    write_json(output_dir / "metrics.json", metrics)

    with (output_dir / "champion_model.pkl").open("wb") as model_file:
        pickle.dump(champion_package, model_file)

    write_step_03_report(
        output_dir=output_dir,
        selected_features=selected_features,
        model_comparison=model_comparison,
        capacity_results=capacity_results,
        champion_row=champion_row,
        existing_alert_metrics=existing_alert_metrics,
    )

    return metrics
