"""What sklearn's ColumnTransformer does, and where it sits relative to a feature store.

Key idea: a transformation is either
  * STATELESS  - depends only on the row (log(amount), amount/avg, fixed buckets)
                 -> can be a feature definition, shared, computed once.
  * STATEFUL   - learns something from the TRAINING data (category->code map,
                 mean/std, imputation value)
                 -> belongs to the MODEL, versioned and shipped with it.
ColumnTransformer is the standard container for the stateful kind.

Run:  uv run --with scikit-learn python demos/04_column_transformer_boundary.py
"""
import io

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

# ---- "feature store" output: RAW feature values, one row per entity/event -----
train_raw = pd.DataFrame(
    {
        "merchant": ["m1"] * 6 + ["m2"] * 3 + ["m3"] * 1,
        "channel": ["web", "web", "app", "app", "app", "web", "app", "web", "app", "web"],
        "amount": [10, 12, 9, 200, 15, 11, 14, 13, 250, 12],
        "txn_count_30d": [3, 4, 2, 9, 5, 3, 4, 4, 8, 3],
    }
)

# ---- ColumnTransformer: "apply THIS transform to THESE columns" ----------------
ct = ColumnTransformer(
    transformers=[
        ("ohe", OneHotEncoder(handle_unknown="ignore"), ["channel"]),
        ("ord", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), ["merchant"]),
        ("scale", StandardScaler(), ["amount"]),
        # anything not listed is dropped by default; here we keep it as-is:
        ("keep", "passthrough", ["txn_count_30d"]),
    ],
    sparse_threshold=0.0,
)

# fit() = LEARN state from training data. This is the important step.
ct.fit(train_raw)
print("=== State learned from the TRAINING data (this is what must ship with the model) ===")
print("channel categories:   ", list(ct.named_transformers_["ohe"].categories_[0]))
print("merchant categories:  ", list(ct.named_transformers_["ord"].categories_[0]))
scaler = ct.named_transformers_["scale"]
print(f"amount mean/std:       {scaler.mean_[0]:.2f} / {scaler.scale_[0]:.2f}")

# transform() = APPLY the learned state. Note: a score-time row with an unseen merchant.
score_raw = pd.DataFrame(
    {"merchant": ["m2", "m9"], "channel": ["app", "kiosk"], "amount": [14, 300], "txn_count_30d": [4, 12]}
)
out = pd.DataFrame(ct.transform(score_raw), columns=ct.get_feature_names_out())
print("\n=== transform(score rows): 'm9' and 'kiosk' were never seen in training ===")
print(out.round(2).to_string(index=False))

# ---- Why the fitted object is part of the MODEL, not the feature store ---------
other_window = train_raw.iloc[::-1].reset_index(drop=True).assign(amount=lambda d: d.amount * 3)
ct2 = ColumnTransformer(ct.transformers, sparse_threshold=0.0).fit(other_window)
same_row = score_raw.iloc[[0]]
print("\n=== Same raw feature row, two training windows -> different model inputs ===")
print("window 1:", ct.transform(same_row).round(2).tolist())
print("window 2:", ct2.transform(same_row).round(2).tolist())

# ---- Shipping it with the model ------------------------------------------------
buf = io.BytesIO()
joblib.dump(ct, buf)  # in practice: log this inside the model artifact
buf.seek(0)
restored = joblib.load(buf)
assert np.allclose(restored.transform(score_raw), ct.transform(score_raw))
print(f"\njoblib round-trip OK ({buf.getbuffer().nbytes} bytes) - persist WITH the model version.")
