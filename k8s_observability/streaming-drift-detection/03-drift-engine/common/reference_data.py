"""The fixed reference distribution both drift modes compare against.

Deliberately matches 01-ingestion's producer.driftBaselineMean/stddev (see
../../01-ingestion/values.yaml) — this IS the "undrifted" state the whole
demo is calibrated around. A real deployment would instead pull this from
02-feature-store's offline store (`amount_source`); generating it inline
here keeps this scaffold's two drift-check scripts runnable without a
working Feast historical-retrieval call, which hasn't been verified yet
(see ../../02-feature-store/README.md).
"""

import os
import random

import pandas as pd


def load_reference(n: int = 1000) -> pd.DataFrame:
    rng = random.Random(42)
    mean = float(os.environ.get("DRIFT_BASELINE_MEAN", "50.0"))
    stddev = float(os.environ.get("REFERENCE_STDDEV", "10.0"))
    rows = [
        {"amount": rng.gauss(mean, stddev), "category": rng.choice(["a", "b", "c"])}
        for _ in range(n)
    ]
    return pd.DataFrame(rows)
