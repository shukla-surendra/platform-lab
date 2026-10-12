"""Generate a small, deterministic e-commerce dataset (stdlib only).

Output (./data):
  customers.csv          2,000 rows
  products.csv              60 rows
  sales/sales_YYYY-MM.csv  ~60,000 rows total, one file per month (tests folder/wildcard queries)
  events.jsonl           5,000 rows of JSON lines (tests JSON parsing in serverless SQL)
Total size is a few MB, so serverless scanning costs are effectively zero.
"""
import csv, json, random
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)
out = Path(__file__).resolve().parent.parent / "data"
(out / "sales").mkdir(parents=True, exist_ok=True)

countries = ["India", "USA", "UK", "Germany", "Singapore", "Australia"]
cats = {"Electronics": (50, 900), "Home": (10, 250), "Books": (5, 40), "Clothing": (15, 150), "Sports": (20, 300)}

with open(out / "customers.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["customer_id", "name", "email", "country", "signup_date"])
    for i in range(1, 2001):
        w.writerow([i, f"Customer {i}", f"user{i}@example.com", random.choice(countries),
                    date(2023, 1, 1) + timedelta(days=random.randint(0, 700))])

products = []
with open(out / "products.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["product_id", "product_name", "category", "unit_price"])
    for i in range(1, 61):
        c = random.choice(list(cats)); lo, hi = cats[c]
        p = (i, f"{c} item {i}", c, round(random.uniform(lo, hi), 2)); products.append(p); w.writerow(p)

order_id = 1
for month in range(1, 13):
    with open(out / "sales" / f"sales_2024-{month:02d}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["order_id", "order_date", "customer_id", "product_id", "quantity", "discount_pct"])
        for _ in range(5000):
            d = date(2024, month, random.randint(1, 28))
            p = random.choice(products)
            w.writerow([order_id, d, random.randint(1, 2000), p[0], random.randint(1, 5), random.choice([0, 0, 0, 5, 10, 20])])
            order_id += 1

with open(out / "events.jsonl", "w") as f:
    for i in range(5000):
        f.write(json.dumps({
            "event_id": i, "ts": (datetime(2024, 6, 1) + timedelta(minutes=i * 7)).isoformat(),
            "customer_id": random.randint(1, 2000),
            "type": random.choice(["view", "add_to_cart", "purchase", "refund"]),
            "device": {"os": random.choice(["ios", "android", "web"]), "version": random.randint(1, 9)},
        }) + "\n")
print("generated into", out)
