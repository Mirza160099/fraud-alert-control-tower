"""Export the champion sklearn pipeline into a browser-readable JSON model.

The Step 5 app is intentionally Vercel-friendly: it runs as static HTML, CSS,
and JavaScript. To avoid a Python server in production, this exporter converts
the fitted preprocessing pipeline and AdaBoost tree ensemble into JSON.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np

from fraud_pipeline import PROJECT_ROOT


DEFAULT_CHAMPION_MODEL_PATH = (
    PROJECT_ROOT / "outputs" / "step_03_model_selection" / "champion_model.pkl"
)
DEFAULT_REFERENCE_PROFILE_PATH = (
    PROJECT_ROOT / "outputs" / "step_04_explainability" / "reference_profile.json"
)
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "step_05_vercel_app" / "model.json"


def parse_args() -> argparse.Namespace:
    """Parse export paths."""

    parser = argparse.ArgumentParser(
        description="Export the Step 3 champion model for browser inference."
    )
    parser.add_argument(
        "--champion-model-path",
        type=Path,
        default=DEFAULT_CHAMPION_MODEL_PATH,
        help="Path to the Step 3 champion model pickle.",
    )
    parser.add_argument(
        "--reference-profile-path",
        type=Path,
        default=DEFAULT_REFERENCE_PROFILE_PATH,
        help="Path to the Step 4 reference profile JSON.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Destination model.json path for the static app.",
    )
    return parser.parse_args()


def to_plain_list(values) -> list:
    """Convert numpy arrays into JSON-safe Python lists."""

    return np.asarray(values).tolist()


def export_tree(estimator) -> dict:
    """Export one fitted decision tree from the AdaBoost ensemble."""

    tree = estimator.tree_
    values = tree.value
    predicted_classes = np.argmax(values[:, 0, :], axis=1).astype(int)

    return {
        "children_left": to_plain_list(tree.children_left),
        "children_right": to_plain_list(tree.children_right),
        "feature": to_plain_list(tree.feature),
        "threshold": to_plain_list(tree.threshold),
        "predicted_class_index": predicted_classes.tolist(),
    }


def build_export_payload(champion_package: dict, reference_profile: dict) -> dict:
    """Build the complete JSON payload consumed by the browser app."""

    pipeline = champion_package["model"]
    preprocessor = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]

    numeric_pipeline = preprocessor.named_transformers_["numeric"]
    categorical_pipeline = preprocessor.named_transformers_["categorical"]

    numeric_features = list(preprocessor.transformers_[0][2])
    categorical_features = list(preprocessor.transformers_[1][2])

    onehot = categorical_pipeline.named_steps["onehot"]

    return {
        "model_name": champion_package["model_name"],
        "threshold": float(champion_package["threshold"]),
        "target_capacity_rate": float(champion_package["target_capacity_rate"]),
        "selected_features": champion_package["selected_features"],
        "feature_schema": champion_package["feature_schema"],
        "reference_profile": reference_profile,
        "preprocessing": {
            "numeric_features": numeric_features,
            "numeric_imputer_statistics": to_plain_list(
                numeric_pipeline.named_steps["imputer"].statistics_
            ),
            "numeric_scaler_mean": to_plain_list(
                numeric_pipeline.named_steps["scaler"].mean_
            ),
            "numeric_scaler_scale": to_plain_list(
                numeric_pipeline.named_steps["scaler"].scale_
            ),
            "categorical_features": categorical_features,
            "categorical_imputer_statistics": to_plain_list(
                categorical_pipeline.named_steps["imputer"].statistics_
            ),
            "categorical_categories": [
                to_plain_list(categories) for categories in onehot.categories_
            ],
            "transformed_feature_names": to_plain_list(
                preprocessor.get_feature_names_out()
            ),
        },
        "adaboost": {
            "classes": to_plain_list(classifier.classes_),
            "n_classes": int(classifier.n_classes_),
            "estimator_weights": to_plain_list(classifier.estimator_weights_),
            "trees": [export_tree(estimator) for estimator in classifier.estimators_],
        },
        "currency_rates_to_usd": {
            "USD": 1.0,
            "GBP": 1.27,
            "EUR": 1.08,
            "INR": 0.012,
            "AED": 0.272,
            "SGD": 0.74,
            "CAD": 0.73,
            "BRL": 0.19,
            "NGN": 0.00067,
        },
    }


def main() -> None:
    """Write model.json for the static prediction app."""

    args = parse_args()

    with args.champion_model_path.open("rb") as model_file:
        champion_package = pickle.load(model_file)

    reference_profile = json.loads(
        args.reference_profile_path.read_text(encoding="utf-8")
    )

    payload = build_export_payload(champion_package, reference_profile)

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
