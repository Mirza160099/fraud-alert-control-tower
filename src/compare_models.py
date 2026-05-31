"""Command-line entry point for Step 3 model comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

from fraud_pipeline import DEFAULT_KIT_DIR
from model_selection import DEFAULT_STEP_03_OUTPUT_DIR, run_model_selection_pipeline


def parse_args() -> argparse.Namespace:
    """Parse optional paths for a reproducible model-selection run."""

    parser = argparse.ArgumentParser(
        description="Compare stronger fraud models and tune capacity thresholds."
    )

    parser.add_argument(
        "--project-kit-dir",
        type=Path,
        default=DEFAULT_KIT_DIR,
        help="Path to the extracted JPMorgan-inspired project kit folder.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_STEP_03_OUTPUT_DIR,
        help="Folder where Step 3 artifacts will be saved.",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of selected features to use for model comparison.",
    )

    parser.add_argument(
        "--target-capacity-rate",
        type=float,
        default=0.05,
        help="Primary investigator capacity target used to select the champion.",
    )

    return parser.parse_args()


def main() -> None:
    """Run the Step 3 comparison workflow."""

    args = parse_args()

    run_model_selection_pipeline(
        project_kit_dir=args.project_kit_dir,
        output_dir=args.output_dir,
        top_n=args.top_n,
        target_capacity_rate=args.target_capacity_rate,
    )


if __name__ == "__main__":
    main()
