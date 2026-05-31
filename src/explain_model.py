"""Command-line entry point for Step 4 explainability."""

from __future__ import annotations

import argparse
from pathlib import Path

from explainability import DEFAULT_STEP_04_OUTPUT_DIR, run_explainability_pipeline
from fraud_pipeline import DEFAULT_KIT_DIR


def parse_args() -> argparse.Namespace:
    """Parse optional paths for the explainability workflow."""

    parser = argparse.ArgumentParser(
        description="Generate global and local explanations for the champion fraud model."
    )

    parser.add_argument(
        "--project-kit-dir",
        type=Path,
        default=DEFAULT_KIT_DIR,
        help="Path to the extracted JPMorgan-inspired project kit folder.",
    )

    parser.add_argument(
        "--champion-model-path",
        type=Path,
        default=Path("outputs") / "step_03_model_selection" / "champion_model.pkl",
        help="Path to the Step 3 champion model pickle.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_STEP_04_OUTPUT_DIR,
        help="Folder where Step 4 explainability artifacts will be saved.",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=25,
        help="Number of highest-risk test cases to explain locally.",
    )

    return parser.parse_args()


def main() -> None:
    """Run Step 4 explainability."""

    args = parse_args()

    run_explainability_pipeline(
        project_kit_dir=args.project_kit_dir,
        champion_model_path=args.champion_model_path,
        output_dir=args.output_dir,
        sample_size=args.sample_size,
    )


if __name__ == "__main__":
    main()
