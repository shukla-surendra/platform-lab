"""Score a batch of data with the persisted model -- the "use some data to
predict" step, run any time after train.py, in a separate process/run.

With no --batch given, samples a fresh, undrifted batch straight from the
holdout pool (data/holdout.parquet) -- i.e. "what does the model do on
ordinary, never-before-seen data" -- and saves the scored result. Pass
--batch to score any parquet file with the right feature columns instead,
including the drifted batches generate_drift.py produces.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from batch_drift_detection.config import DATA_DIR, FEATURE_NAMES, HOLDOUT_PATH, PREDICTION_COLUMN
from batch_drift_detection.model_io import load_model


def predict(batch_df: pd.DataFrame) -> pd.DataFrame:
    model = load_model()
    batch_df = batch_df.copy()
    batch_df[PREDICTION_COLUMN] = model.predict(batch_df[FEATURE_NAMES])
    return batch_df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, default=None, help="Parquet file to score (default: a fresh sample from holdout)")
    parser.add_argument("--n", type=int, default=800, help="Sample size when no --batch is given")
    parser.add_argument("--seed", type=int, default=1, help="Sample seed when no --batch is given")
    parser.add_argument("--out", type=Path, default=None, help="Output parquet path (default: derived from input name)")
    args = parser.parse_args()

    if args.batch is not None:
        batch_df = pd.read_parquet(args.batch)
        out_path = args.out or DATA_DIR / f"scored_{args.batch.stem}.parquet"
    else:
        if not HOLDOUT_PATH.exists():
            raise FileNotFoundError(f"No holdout pool at {HOLDOUT_PATH} -- run `train.py` first.")
        holdout_df = pd.read_parquet(HOLDOUT_PATH)
        batch_df = holdout_df.sample(n=args.n, random_state=args.seed).reset_index(drop=True)
        out_path = args.out or DATA_DIR / "scored_clean_batch.parquet"

    scored = predict(batch_df)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    scored.to_parquet(out_path)

    pred_balance = scored[PREDICTION_COLUMN].value_counts(normalize=True).sort_index()
    print(f"Scored {len(scored)} rows -> {out_path}")
    print(f"Predicted class balance:\n{pred_balance}")


if __name__ == "__main__":
    main()
