"""Problem #1: training/serving skew.

The feature is "average transaction amount over the last 30 days".
The data-science team computes it in a batch job to build the training set.
Months later the backend team re-implements it inside the prediction service
because it can't run a Spark job per request. Both read the same words in a
ticket — "avg amount, last 30 days" — and both are "correct".

Run:  uv run python demos/01_training_serving_skew.py
"""
import pandas as pd

from data import make_transactions

txns = make_transactions()
AS_OF = txns["ts"].max()


# --- Implementation A: what the training pipeline does ----------------------
def avg_amount_30d_batch(df: pd.DataFrame, customer_id: int, as_of: pd.Timestamp) -> float:
    w = df[(df.customer_id == customer_id) & (df.ts > as_of - pd.Timedelta(days=30)) & (df.ts <= as_of)]
    w = w[w.amount > 0]  # refunds are not "purchases", so exclude them
    return w.amount.mean() if len(w) else float("nan")


# --- Implementation B: what the serving code does ---------------------------
# Fetches the customer's recent rows from the transactions DB (cheap: LIMIT 30)
# and averages them. Different window semantics (30 events, not 30 days) and
# refunds are left in. Nobody decided this; it just fell out of the SQL.
def avg_amount_30d_service(df: pd.DataFrame, customer_id: int, as_of: pd.Timestamp) -> float:
    w = df[(df.customer_id == customer_id) & (df.ts <= as_of)].sort_values("ts").tail(30)
    return w.amount.mean() if len(w) else float("nan")


ids = sorted(txns.customer_id.unique())
offline = pd.Series({c: avg_amount_30d_batch(txns, c, AS_OF) for c in ids})
online = pd.Series({c: avg_amount_30d_service(txns, c, AS_OF) for c in ids})

both = pd.DataFrame({"training_value": offline, "serving_value": online}).dropna()
both["abs_diff"] = (both.training_value - both.serving_value).abs()
both["rel_diff"] = both.abs_diff / both.training_value.abs()

# Stand-in for a model: flag the customer as "high spender" above a threshold
# picked on the training-side distribution.
threshold = both.training_value.median()
flip = (both.training_value > threshold) != (both.serving_value > threshold)

print("=== Two implementations of 'avg amount, last 30 days' ===")
print(f"customers compared:                     {len(both)}")
print(f"differ by > 10%:                        {(both.rel_diff > 0.10).mean():.0%}")
print(f"decision flips at the same threshold:   {flip.mean():.0%}")
print("\nlargest disagreements:")
print(both.sort_values("abs_diff", ascending=False).head(5).round(2).to_string())

print(
    "\nNo exception was raised, no test failed, latency is fine. The model just\n"
    "sees inputs in production that it never saw in training, and its accuracy\n"
    "quietly degrades. That silent gap is training/serving skew.\n"
)


# --- The fix: ONE definition, used by both paths ----------------------------
# (The point isn't that you can't write one function — it's that with two
# pipelines, two teams and two languages, nothing FORCES you to. A feature
# store's job is to make the single definition the only path. See demo 3.)
served = pd.Series({c: avg_amount_30d_batch(txns, c, AS_OF) for c in ids})
print("=== Same function on both sides ===")
print(f"max |training - serving| = {(offline - served).abs().max():.6f}")
