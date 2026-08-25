"""Generate new synthetic "current" batches from the holdout pool, with
data drift, concept drift, both, or neither injected -- the "later, we
should have the ability to generate new synthetic data where we have
drift" step, run any time after train.py, as its own separate step.

Both injection mechanics are the same ones already verified (with real
before/after numbers) in
../../evidently-monitoring-demo/drift_types_with_evidently.ipynb -- reused
here rather than re-derived, and turned into a persisted-artifact CLI
instead of notebook cells:

  - Data drift (covariate shift, P(X) changes): rescale one feature
    column. The input->output relationship itself is untouched -- `target`
    is copied through unchanged. This is what DataDriftPreset is built to
    catch.
  - Concept drift (P(Y|X) changes): take a FRESH, unperturbed sample (no
    feature shift at all) and flip the true label for the half of rows
    where a chosen feature is above its median -- as if the real-world
    rule connecting that feature to the outcome reversed for part of the
    population. DataDriftPreset stays quiet (no feature was touched);
    only a ground-truth-aware check (ClassificationPreset, in monitor.py)
    can see this one. See
    ../../../docs/tools/evidently/drift-detection-concepts.md for why
    that split matters.

Neither injection scores the batch (no `prediction` column) -- that's
predict.py's job, and monitor.py calls predict() itself if a scored batch
isn't handed to it. Keeping generation and scoring as separate steps means
a batch can be inspected (or handed to a completely different model)
before anything predicts on it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from batch_drift_detection.config import DATA_DIR, HOLDOUT_PATH, TARGET_COLUMN

DEFAULT_DATA_DRIFT_FEATURE = "feature_0"
DEFAULT_CONCEPT_DRIFT_SLICE_FEATURE = "feature_1"


def sample_batch(holdout_df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    return holdout_df.sample(n=n, random_state=seed).reset_index(drop=True)


def inject_data_drift(batch_df: pd.DataFrame, feature: str = DEFAULT_DATA_DRIFT_FEATURE, scale: float = 1.8, shift: float = 3.0) -> pd.DataFrame:
    batch_df = batch_df.copy()
    batch_df[feature] = batch_df[feature] * scale + shift
    return batch_df


def inject_concept_drift(batch_df: pd.DataFrame, slice_feature: str = DEFAULT_CONCEPT_DRIFT_SLICE_FEATURE) -> pd.DataFrame:
    batch_df = batch_df.copy()
    flip_mask = batch_df[slice_feature] > batch_df[slice_feature].median()
    batch_df[TARGET_COLUMN] = np.where(flip_mask, 1 - batch_df[TARGET_COLUMN], batch_df[TARGET_COLUMN])
    return batch_df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=["clean", "data", "concept", "both"], default="both")
    parser.add_argument("--n", type=int, default=800)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--feature", default=DEFAULT_DATA_DRIFT_FEATURE, help="Feature to rescale for data drift")
    parser.add_argument("--scale", type=float, default=1.8)
    parser.add_argument("--shift", type=float, default=3.0)
    parser.add_argument("--slice-feature", default=DEFAULT_CONCEPT_DRIFT_SLICE_FEATURE, help="Feature whose median splits the label-flip slice for concept drift")
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()

    if not HOLDOUT_PATH.exists():
        raise FileNotFoundError(f"No holdout pool at {HOLDOUT_PATH} -- run `train.py` first.")
    holdout_df = pd.read_parquet(HOLDOUT_PATH)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    kinds = ["clean", "data", "concept"] if args.kind == "both" else [args.kind]
    for kind in kinds:
        batch = sample_batch(holdout_df, n=args.n, seed=args.seed)
        if kind == "data":
            batch = inject_data_drift(batch, feature=args.feature, scale=args.scale, shift=args.shift)
        elif kind == "concept":
            batch = inject_concept_drift(batch, slice_feature=args.slice_feature)

        out_path = args.out_dir / f"current_{kind}.parquet"
        batch.to_parquet(out_path)
        print(f"[{kind}] {len(batch)} rows -> {out_path}")


if __name__ == "__main__":
    main()
