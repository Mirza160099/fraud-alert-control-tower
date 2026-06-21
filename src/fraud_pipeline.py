"""Step 2 fraud modeling pipeline.

This module turns the raw project-kit CSV files into a reproducible baseline
fraud model. It is deliberately written as regular Python instead of notebook
cells so every cleaning, feature engineering, and modeling decision can be
reviewed, tested, and reused later in an app.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# Resolve the repository root from this file location.
# src/fraud_pipeline.py -> project root is one level above src.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Keep the extracted kit path in one place so a reviewer can change it easily.
DEFAULT_KIT_DIR = (
    PROJECT_ROOT
    / "work"
    / "project_kit"
    / "02_JPMorgan_Explainable_Fraud_Alert_Prioritization_Project_Kit"
)

# Save Step 2 artifacts under outputs because these are user-facing deliverables.
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "step_02_modeling"

# Normalize country labels so UK and GB are treated as the same business region.
COUNTRY_NORMALIZATION = {"GB": "UK"}

# These columns are never allowed into the model as predictive features.
# They are identifiers, target fields, or existing operational decisions.
LEAKAGE_OR_ID_COLUMNS = {
    "transaction_id",
    "customer_id",
    "merchant_id",
    "fraud_label",
    "alert_generated",
}


@dataclass(frozen=True)
class DatasetBundle:
    """Container for the three raw source tables."""

    transactions: pd.DataFrame
    customers: pd.DataFrame
    merchants: pd.DataFrame


@dataclass(frozen=True)
class SplitData:
    """Container for train, validation, and test splits."""

    X_train: pd.DataFrame
    X_validation: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_validation: pd.Series
    y_test: pd.Series
    test_context: pd.DataFrame


def load_raw_tables(project_kit_dir: Path) -> DatasetBundle:
    """Load the raw transaction, customer, and merchant tables from CSV files."""

    raw_dir = project_kit_dir / "B_Dataset" / "raw"

    # Parse event_ts immediately so time-based feature engineering is reliable.
    transactions = pd.read_csv(raw_dir / "transactions.csv", parse_dates=["event_ts"])

    # Customers and merchants are loaded separately because they represent
    # profile tables that need left joins onto the transaction grain.
    customers = pd.read_csv(raw_dir / "customers.csv")
    merchants = pd.read_csv(raw_dir / "merchants.csv")

    return DatasetBundle(
        transactions=transactions,
        customers=customers,
        merchants=merchants,
    )


def normalize_country(series: pd.Series) -> pd.Series:
    """Standardize country codes used by transaction and customer tables."""

    return series.replace(COUNTRY_NORMALIZATION)


def build_modeling_table(bundle: DatasetBundle) -> pd.DataFrame:
    """Clean, join, and engineer a transaction-level modeling table."""

    transactions = bundle.transactions.copy()
    customers = bundle.customers.copy()
    merchants = bundle.merchants.copy()

    # Standardize country codes before comparing home country to transaction
    # country. This avoids treating UK and GB as different when they represent
    # the same region in this synthetic dataset.
    transactions["txn_country"] = normalize_country(transactions["txn_country"])
    customers["home_country"] = normalize_country(customers["home_country"])

    # The data dictionary says tenure_months is an integer, but the raw file
    # contains date-like strings such as 1970-01-01. We preserve the issue as a
    # quality flag and avoid pretending it is a valid numeric feature.
    customers["tenure_months_numeric"] = pd.to_numeric(
        customers["tenure_months"], errors="coerce"
    )
    customers["tenure_months_missing_or_invalid_flag"] = customers[
        "tenure_months_numeric"
    ].isna().astype(int)
    customers = customers.drop(columns=["tenure_months", "tenure_months_numeric"])

    # Rename the merchant table's risk score so it does not collide with the
    # transaction table's merchant_risk_score column.
    merchants = merchants.rename(
        columns={"merchant_risk_score": "merchant_profile_risk_score"}
    )

    # Left join keeps every transaction, which is the correct modeling grain.
    # Indicator columns let us measure and model missing customer/merchant
    # profiles without silently dropping transactions.
    modeling_table = transactions.merge(
        customers,
        on="customer_id",
        how="left",
        indicator="customer_join_status",
    )
    modeling_table = modeling_table.merge(
        merchants,
        on="merchant_id",
        how="left",
        indicator="merchant_join_status",
    )

    # Convert join status into model-friendly flags.
    modeling_table["customer_profile_missing_flag"] = (
        modeling_table["customer_join_status"] != "both"
    ).astype(int)
    modeling_table["merchant_profile_missing_flag"] = (
        modeling_table["merchant_join_status"] != "both"
    ).astype(int)
    modeling_table = modeling_table.drop(
        columns=["customer_join_status", "merchant_join_status"]
    )

    # Add time features that are easy to explain to an interviewer or business
    # stakeholder. event_ts itself is not used directly by the model.
    modeling_table["event_month"] = modeling_table["event_ts"].dt.month
    modeling_table["event_dayofweek"] = modeling_table["event_ts"].dt.dayofweek
    modeling_table["event_is_weekend"] = (
        modeling_table["event_dayofweek"].isin([5, 6])
    ).astype(int)

    # Log amount reduces the influence of very large transaction outliers while
    # keeping the original amount available for business interpretation.
    modeling_table["amount_log1p"] = np.log1p(
        modeling_table["transaction_amount_usd"].clip(lower=0)
    )

    # Cross-border behavior is a useful fraud signal when home country is known.
    # Missing customer profiles are handled separately by customer_profile_missing_flag.
    modeling_table["cross_border_flag"] = np.where(
        modeling_table["home_country"].notna(),
        (modeling_table["txn_country"] != modeling_table["home_country"]).astype(int),
        0,
    )

    return modeling_table


def get_candidate_features(modeling_table: pd.DataFrame) -> list[str]:
    """Return model-eligible columns after removing IDs and leakage fields."""

    blocked_columns = LEAKAGE_OR_ID_COLUMNS.union({"event_ts"})

    # Keep engineered and profile features, but remove identifiers, target, and
    # existing alert output. This prevents leakage and memorization.
    return [
        column
        for column in modeling_table.columns
        if column not in blocked_columns
    ]


def split_modeling_data(
    modeling_table: pd.DataFrame,
    candidate_features: list[str],
    random_state: int = 42,
) -> SplitData:
    """Create stratified train, validation, and test sets."""

    X = modeling_table[candidate_features]
    y = modeling_table["fraud_label"].astype(int)

    # Keep operational fields outside the model so they can be used later for
    # benchmarking and reporting.
    context_columns = [
        "transaction_id",
        "event_ts",
        "alert_generated",
        "fraud_label",
    ]
    context = modeling_table[context_columns].copy()

    # First hold out a final test set. This remains untouched until evaluation.
    X_train_validation, X_test, y_train_validation, y_test, context_train_validation, context_test = train_test_split(
        X,
        y,
        context,
        test_size=0.20,
        stratify=y,
        random_state=random_state,
    )

    # Then split the remaining data into training and validation sets. The
    # validation set is where we choose the classification threshold.
    X_train, X_validation, y_train, y_validation = train_test_split(
        X_train_validation,
        y_train_validation,
        test_size=0.25,
        stratify=y_train_validation,
        random_state=random_state,
    )

    return SplitData(
        X_train=X_train,
        X_validation=X_validation,
        X_test=X_test,
        y_train=y_train,
        y_validation=y_validation,
        y_test=y_test,
        test_context=context_test,
    )


def make_one_hot_encoder() -> OneHotEncoder:
    """Create a dense one-hot encoder across supported scikit-learn versions."""

    # scikit-learn 1.2 renamed sparse to sparse_output. This try/except keeps
    # the code portable for reviewers with slightly different environments.
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def infer_column_types(X: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Separate numeric and categorical features for preprocessing."""

    categorical_features = X.select_dtypes(
        include=["object", "category", "string"]
    ).columns.tolist()
    numeric_features = [
        column for column in X.columns if column not in categorical_features
    ]

    return numeric_features, categorical_features


def make_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """Build preprocessing for numeric and categorical model inputs."""

    numeric_features, categorical_features = infer_column_types(X)

    # Numeric values get median imputation and scaling. Scaling helps logistic
    # regression coefficients behave consistently across features.
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    # Categorical values get most-frequent imputation and one-hot encoding.
    # Unknown categories are ignored so the later app does not crash on a new
    # country, channel, or merchant category value.
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", make_one_hot_encoder()),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )


def bin_feature_for_mutual_info(feature: pd.Series) -> pd.Series:
    """Convert one feature into discrete buckets for source-level MI scoring."""

    # Categorical and binary columns are already discrete enough for mutual
    # information. Missing values are filled later in discrete_mutual_info.
    if not pd.api.types.is_numeric_dtype(feature):
        return feature

    unique_values = feature.nunique(dropna=True)

    # Keep low-cardinality numeric features, such as flags and hour values, as
    # their original values because those values already represent categories.
    if unique_values <= 10:
        return feature

    # Bucket continuous numeric values into quantiles. This makes the MI score
    # source-level and explainable rather than dependent on one-hot encodings.
    try:
        return pd.qcut(feature, q=min(10, unique_values), duplicates="drop")
    except ValueError:
        return pd.cut(feature, bins=min(10, unique_values))


def discrete_mutual_info(feature: pd.Series, target: pd.Series) -> float:
    """Calculate mutual information for one already-discretized source feature."""

    prepared = pd.DataFrame(
        {
            "feature": feature.astype("object").where(
                feature.notna(), "__MISSING__"
            ),
            "target": target.astype(int),
        }
    )
    row_count = len(prepared)

    # Build the joint and marginal probability tables needed for the mutual
    # information formula: sum p(x,y) * log(p(x,y) / (p(x) * p(y))).
    joint_counts = (
        prepared.value_counts(["feature", "target"])
        .rename("count")
        .reset_index()
    )
    feature_probabilities = prepared["feature"].value_counts() / row_count
    target_probabilities = prepared["target"].value_counts() / row_count

    mutual_information = 0.0

    for row in joint_counts.itertuples(index=False):
        joint_probability = row.count / row_count
        expected_probability = (
            feature_probabilities[row.feature] * target_probabilities[row.target]
        )
        mutual_information += joint_probability * np.log(
            joint_probability / expected_probability
        )

    return float(mutual_information)


def select_top_features_by_mutual_info(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    top_n: int,
    random_state: int = 42,
) -> pd.DataFrame:
    """Rank source features by mutual information against the fraud label."""

    # random_state is accepted so the function signature stays stable if we add
    # a stochastic selector later. The current binned MI calculation is
    # deterministic, so no random generator is required.
    _ = random_state

    source_scores = []

    # Score each original feature directly. This avoids a common interview-risk
    # problem where one-hot encoded categories dominate the feature list and the
    # final explanation becomes harder for business stakeholders to understand.
    for source_feature in X_train.columns:
        binned_feature = bin_feature_for_mutual_info(X_train[source_feature])
        source_scores.append(
            {
                "source_feature": source_feature,
                "mutual_info": discrete_mutual_info(binned_feature, y_train),
            }
        )

    source_scores = (
        pd.DataFrame(source_scores)
        .sort_values("mutual_info", ascending=False)
        .reset_index(drop=True)
    )
    source_scores["rank"] = source_scores.index + 1

    return source_scores.head(top_n)


def build_baseline_model(X_train: pd.DataFrame) -> Pipeline:
    """Create the baseline model pipeline for the selected top features."""

    preprocessor = make_preprocessor(X_train)

    # Logistic regression is a strong first model because it gives transparent
    # coefficients, trains quickly, and works well with one-hot encoded data.
    # class_weight balanced helps the model pay attention to rare fraud cases.
    classifier = LogisticRegression(
        class_weight="balanced",
        max_iter=2000,
        solver="lbfgs",
        random_state=42,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def choose_threshold(y_true: pd.Series, predicted_probabilities: np.ndarray) -> dict:
    """Choose a validation threshold using the best F1 score."""

    precision, recall, thresholds = precision_recall_curve(
        y_true, predicted_probabilities
    )

    # precision_recall_curve returns one extra precision/recall pair without a
    # matching threshold, so we evaluate only the threshold-aligned values.
    if len(thresholds) == 0:
        return {
            "threshold": 0.50,
            "precision": float(precision_score(y_true, predicted_probabilities >= 0.50, zero_division=0)),
            "recall": float(recall_score(y_true, predicted_probabilities >= 0.50, zero_division=0)),
            "f1": float(f1_score(y_true, predicted_probabilities >= 0.50, zero_division=0)),
        }

    aligned_precision = precision[:-1]
    aligned_recall = recall[:-1]
    f1_scores = (
        2
        * aligned_precision
        * aligned_recall
        / np.maximum(aligned_precision + aligned_recall, 1e-12)
    )

    best_index = int(np.nanargmax(f1_scores))

    return {
        "threshold": float(thresholds[best_index]),
        "precision": float(aligned_precision[best_index]),
        "recall": float(aligned_recall[best_index]),
        "f1": float(f1_scores[best_index]),
    }


def classify_priority(probability: float, threshold: float) -> str:
    """Translate fraud probability into an investigation-friendly priority tier."""

    # The threshold separates predicted legitimate from predicted fraud.
    # Higher bands help an investigator decide what to work first. These
    # labels intentionally match the frontend score, queue, and report export.
    if probability >= max(0.82, threshold):
        return "Critical"
    if probability >= threshold:
        return "High"
    if probability >= 0.35:
        return "Medium"
    return "Low"


def classification_metrics(
    y_true: pd.Series,
    predicted_probabilities: np.ndarray,
    threshold: float,
) -> dict:
    """Calculate common classification metrics at the chosen threshold."""

    predicted_labels = (predicted_probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted_labels).ravel()

    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predicted_labels)),
        "precision": float(precision_score(y_true, predicted_labels, zero_division=0)),
        "recall": float(recall_score(y_true, predicted_labels, zero_division=0)),
        "f1": float(f1_score(y_true, predicted_labels, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, predicted_probabilities)),
        "average_precision_pr_auc": float(
            average_precision_score(y_true, predicted_probabilities)
        ),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }


def binary_policy_metrics(y_true: pd.Series, policy_labels: pd.Series) -> dict:
    """Evaluate an existing binary alert policy against the fraud label."""

    tn, fp, fn, tp = confusion_matrix(y_true, policy_labels).ravel()

    return {
        "accuracy": float(accuracy_score(y_true, policy_labels)),
        "precision": float(precision_score(y_true, policy_labels, zero_division=0)),
        "recall": float(recall_score(y_true, policy_labels, zero_division=0)),
        "f1": float(f1_score(y_true, policy_labels, zero_division=0)),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }


def make_test_prediction_table(
    test_context: pd.DataFrame,
    y_test: pd.Series,
    predicted_probabilities: np.ndarray,
    threshold: float,
) -> pd.DataFrame:
    """Create a reviewer-friendly table of test-set predictions."""

    predictions = test_context.copy()
    predictions["actual_fraud_label"] = y_test.to_numpy()
    predictions["predicted_fraud_probability"] = predicted_probabilities
    predictions["predicted_fraud_label"] = (
        predictions["predicted_fraud_probability"] >= threshold
    ).astype(int)
    predictions["priority_tier"] = predictions["predicted_fraud_probability"].apply(
        lambda probability: classify_priority(probability, threshold)
    )

    return predictions.sort_values(
        "predicted_fraud_probability", ascending=False
    ).reset_index(drop=True)


def build_feature_schema(
    modeling_table: pd.DataFrame,
    selected_features: list[str],
) -> dict:
    """Create input metadata for the later app and prediction API."""

    schema = {}
    numeric_features, categorical_features = infer_column_types(
        modeling_table[selected_features]
    )

    # Numeric features get min, max, median, and mean values. These are useful
    # defaults for sliders or number inputs in a future app.
    for feature in numeric_features:
        values = modeling_table[feature].dropna()
        schema[feature] = {
            "type": "numeric",
            "min": float(values.min()) if len(values) else None,
            "max": float(values.max()) if len(values) else None,
            "median": float(values.median()) if len(values) else None,
            "mean": float(values.mean()) if len(values) else None,
        }

    # Categorical features get a sorted list of known categories. A future app
    # can show these as dropdown options and still rely on handle_unknown for
    # genuinely new values.
    for feature in categorical_features:
        categories = (
            modeling_table[feature]
            .dropna()
            .astype(str)
            .sort_values()
            .unique()
            .tolist()
        )
        schema[feature] = {
            "type": "categorical",
            "categories": categories,
            "default": categories[0] if categories else None,
        }

    return schema


def write_json(path: Path, payload: dict) -> None:
    """Write a dictionary as readable JSON."""

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown_report(
    output_dir: Path,
    top_features: pd.DataFrame,
    metrics: dict,
    selected_features: list[str],
) -> None:
    """Write a Step 2 progress report from the training run."""

    feature_lines = "\n".join(
        f"| {int(row.rank)} | `{row.source_feature}` | {row.mutual_info:.6f} |"
        for row in top_features.itertuples(index=False)
    )

    report = f"""# Progress Report - Step 02: Modeling Pipeline

## What We Built

This step created a fully commented Python modeling pipeline for cleaning, joining, feature engineering, top-10 feature selection, and baseline model training.

## Cleaning and Feature Engineering Applied

1. Loaded raw transactions, customers, and merchants.
2. Parsed `event_ts` as a real datetime.
3. Normalized `GB` to `UK` for country consistency.
4. Preserved all transactions as the modeling grain.
5. Left joined customer and merchant profile data.
6. Added `customer_profile_missing_flag` because 822 transactions do not match a customer profile.
7. Added `merchant_profile_missing_flag`, although merchant joins are currently complete.
8. Flagged broken `tenure_months` values instead of using them as numeric months.
9. Added event month, day of week, and weekend features.
10. Added `amount_log1p` to reduce the effect of extreme transaction amounts.
11. Added `cross_border_flag` for transaction country vs home country mismatch.
12. Excluded IDs, target, and `alert_generated` from model features to avoid leakage.
13. Saved a feature schema with ranges and categories for the future app.

## Top 10 Features by Mutual Information

| Rank | Feature | Mutual information |
|---:|---|---:|
{feature_lines}

## Baseline Model

The baseline model is logistic regression with:

- median imputation and standard scaling for numeric features
- most-frequent imputation and one-hot encoding for categorical features
- `class_weight="balanced"` to handle rare fraud cases
- threshold chosen on the validation set using best F1 score

Selected feature list:

{chr(10).join(f"- `{feature}`" for feature in selected_features)}

## Validation Threshold

- Threshold: `{metrics["validation_threshold"]["threshold"]:.4f}`
- Validation precision: `{metrics["validation_threshold"]["precision"]:.4f}`
- Validation recall: `{metrics["validation_threshold"]["recall"]:.4f}`
- Validation F1: `{metrics["validation_threshold"]["f1"]:.4f}`

## Test Performance

- Accuracy: `{metrics["test_model_metrics"]["accuracy"]:.4f}`
- Precision: `{metrics["test_model_metrics"]["precision"]:.4f}`
- Recall: `{metrics["test_model_metrics"]["recall"]:.4f}`
- F1: `{metrics["test_model_metrics"]["f1"]:.4f}`
- ROC-AUC: `{metrics["test_model_metrics"]["roc_auc"]:.4f}`
- PR-AUC: `{metrics["test_model_metrics"]["average_precision_pr_auc"]:.4f}`
- True positives: `{metrics["test_model_metrics"]["true_positives"]}`
- False positives: `{metrics["test_model_metrics"]["false_positives"]}`
- False negatives: `{metrics["test_model_metrics"]["false_negatives"]}`
- True negatives: `{metrics["test_model_metrics"]["true_negatives"]}`

## Existing Alert Benchmark on the Same Test Set

- Precision: `{metrics["existing_alert_benchmark"]["precision"]:.4f}`
- Recall: `{metrics["existing_alert_benchmark"]["recall"]:.4f}`
- F1: `{metrics["existing_alert_benchmark"]["f1"]:.4f}`
- True positives: `{metrics["existing_alert_benchmark"]["true_positives"]}`
- False positives: `{metrics["existing_alert_benchmark"]["false_positives"]}`
- False negatives: `{metrics["existing_alert_benchmark"]["false_negatives"]}`
- True negatives: `{metrics["existing_alert_benchmark"]["true_negatives"]}`

## Interview Talking Point

This model is not positioned as a final production model. It is a controlled baseline that demonstrates disciplined fraud modeling: leakage prevention, class imbalance handling, feature selection on training data only, validation-based thresholding, and an operational comparison against existing alerts.

## Artifacts Created

- `top_10_features_mutual_info.csv`
- `metrics.json`
- `test_predictions.csv`
- `feature_schema.json`
- `fraud_baseline_model.pkl`
"""

    (output_dir / "progress_report_step_02.md").write_text(report, encoding="utf-8")


def run_training_pipeline(
    project_kit_dir: Path = DEFAULT_KIT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    top_n: int = 10,
) -> dict:
    """Run the complete Step 2 fraud modeling workflow."""

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load and transform the raw data into a single transaction-level table.
    bundle = load_raw_tables(project_kit_dir)
    modeling_table = build_modeling_table(bundle)

    # Choose eligible model inputs after leakage and identifier controls.
    candidate_features = get_candidate_features(modeling_table)

    # Split first so feature selection and threshold choice do not peek at test.
    split_data = split_modeling_data(modeling_table, candidate_features)

    # Rank all candidate features using training data only.
    top_features = select_top_features_by_mutual_info(
        split_data.X_train,
        split_data.y_train,
        top_n=top_n,
    )
    selected_features = top_features["source_feature"].tolist()

    # Train the baseline only on the selected top features.
    model = build_baseline_model(split_data.X_train[selected_features])
    model.fit(split_data.X_train[selected_features], split_data.y_train)

    # Pick the probability threshold using validation data, not the test set.
    validation_probabilities = model.predict_proba(
        split_data.X_validation[selected_features]
    )[:, 1]
    threshold_info = choose_threshold(
        split_data.y_validation,
        validation_probabilities,
    )
    threshold = threshold_info["threshold"]

    # Evaluate the final model one time on the held-out test set.
    test_probabilities = model.predict_proba(split_data.X_test[selected_features])[:, 1]
    test_model_metrics = classification_metrics(
        split_data.y_test,
        test_probabilities,
        threshold,
    )

    # Compare against the existing alert_generated flag on the same test rows.
    existing_alert_benchmark = binary_policy_metrics(
        split_data.y_test,
        split_data.test_context["alert_generated"].astype(int),
    )

    # Save the scored test transactions for review and later dashboard work.
    prediction_table = make_test_prediction_table(
        split_data.test_context,
        split_data.y_test,
        test_probabilities,
        threshold,
    )

    # Save input metadata now so the later app can use the same selected
    # features without guessing valid ranges or category values.
    feature_schema = build_feature_schema(modeling_table, selected_features)

    # Package the model with metadata the later app will need.
    model_package = {
        "model": model,
        "selected_features": selected_features,
        "threshold": threshold,
        "feature_schema": feature_schema,
        "feature_selection_method": "binned_source_mutual_information",
        "priority_policy": {
            "Critical": f"probability >= max(0.82, {threshold:.6f})",
            "High": f"probability >= {threshold:.6f}",
            "Medium": f"0.35 <= probability < {threshold:.6f}",
            "Low": "probability < 0.35",
        },
    }

    metrics = {
        "row_counts": {
            "raw_transactions": int(len(bundle.transactions)),
            "modeling_table": int(len(modeling_table)),
            "train": int(len(split_data.X_train)),
            "validation": int(len(split_data.X_validation)),
            "test": int(len(split_data.X_test)),
        },
        "fraud_rate": float(modeling_table["fraud_label"].mean()),
        "selected_features": selected_features,
        "validation_threshold": threshold_info,
        "test_model_metrics": test_model_metrics,
        "existing_alert_benchmark": existing_alert_benchmark,
    }

    # Write all Step 2 deliverables in stable, reviewable formats.
    top_features.to_csv(output_dir / "top_10_features_mutual_info.csv", index=False)
    prediction_table.to_csv(output_dir / "test_predictions.csv", index=False)
    write_json(output_dir / "feature_schema.json", feature_schema)
    write_json(output_dir / "metrics.json", metrics)
    write_markdown_report(output_dir, top_features, metrics, selected_features)

    with (output_dir / "fraud_baseline_model.pkl").open("wb") as model_file:
        pickle.dump(model_package, model_file)

    return metrics
