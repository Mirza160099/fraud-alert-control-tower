"""Command-line entry point for Step 2 model training.

This file stays intentionally small. The detailed, heavily commented logic
lives in ``fraud_pipeline.py`` so it can be reused later by a notebook, an API,
or a Vercel-facing prediction service.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fraud_pipeline import DEFAULT_KIT_DIR, DEFAULT_OUTPUT_DIR, run_training_pipeline


def parse_args() -> argparse.Namespace:
    """Parse optional paths so the project can run on another machine later."""

    parser = argparse.ArgumentParser(
        description="Train the explainable fraud alert prioritization baseline model."
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
        default=DEFAULT_OUTPUT_DIR,
        help="Folder where model artifacts, metrics, and reports will be saved.",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of source features to keep after mutual information ranking.",
    )

    return parser.parse_args()


def main() -> None:
    """Run the complete Step 2 training workflow from the command line."""

    args = parse_args()

    run_training_pipeline(
        project_kit_dir=args.project_kit_dir,
        output_dir=args.output_dir,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
