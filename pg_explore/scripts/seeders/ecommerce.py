"""Seeds the ecommerce schema: customers, categories, products, orders, order_items, payments.

Deliberately shapes purchase history for a set of customers so the classic
"bought X but never Y" (set-operation) practice query has a known-correct answer:
  - customers  1-20  buy a Laptop, never a Mouse           -> expected result
  - customers 21-35  buy both a Laptop and a Mouse         -> excluded
  - customers 36-45  buy a Mouse, never a Laptop           -> excluded
  - customers 46+    shop the full catalog at random       -> incidental data
"""
import random
import sys
from datetime import date
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import get_conn  # noqa: E402

fake = Faker()
Faker.seed(7)
random.seed(7)

NUM_CUSTOMERS = 150
LAPTOP_ONLY_IDS = range(1, 21)
LAPTOP_AND_MOUSE_IDS = range(21, 36)
MOUSE_ONLY_IDS = range(36, 46)

CATEGORY_PRODUCTS = {
    "Electronics": ["Laptop", "Mouse", "Keyboard", "Monitor", "Webcam", "Headphones", "Tablet", "Smartphone", "External Hard Drive", "Bluetooth Speaker", "Smartwatch", "Router"],
    "Books": ["Mystery Novel", "Cookbook", "Biography", "Science Fiction Novel", "Self-Help Guide", "History Book", "Children's Storybook", "Poetry Collection"],
    "Home & Kitchen": ["Blender", "Coffee Maker", "Air Fryer", "Toaster", "Cookware Set", "Vacuum Cleaner", "Bedding Set", "Table Lamp"],
    "Toys & Games": ["Building Blocks Set", "Board Game", "Puzzle", "Action Figure", "Remote Control Car", "Doll House", "Card Game"],
    "Sports & Outdoors": ["Yoga Mat", "Dumbbell Set", "Tent", "Bicycle Helmet", "Running Shoes", "Water Bottle", "Camping Chair"],
    "Beauty & Personal Care": ["Shampoo", "Moisturizer", "Electric Toothbrush", "Hair Dryer", "Perfume", "Makeup Kit"],
    "Grocery": ["Organic Coffee", "Olive Oil", "Pasta", "Green Tea", "Almond Butter", "Granola Bars"],
    "Office Supplies": ["Notebook", "Desk Organizer", "Stapler", "Printer Paper", "Ballpoint Pens", "Whiteboard"],
}
VARIANT_PREFIXES = ["", "", "Premium ", "Deluxe ", "Compact ", "Pro "]

ORDER_STATUSES = ["delivered"] * 6 + ["shipped"] * 2 + ["pending"] + ["cancelled"]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "gift_card"]
PAYMENT_STATUSES = ["completed"] * 9 + ["refunded"]


def random_date(start_year=2022, end_year=2025):
    return fake.date_between(start_date=date(start_year, 1, 1), end_date=date(end_year, 12, 31))


def seed():
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute(
            "TRUNCATE TABLE ecommerce.payments, ecommerce.order_items, ecommerce.orders, "
            "ecommerce.products, ecommerce.categories, ecommerce.customers RESTART IDENTITY CASCADE"
        )
        category_ids = {}
        for cat_name in CATEGORY_PRODUCTS:
            cur.execute(
                "INSERT INTO ecommerce.categories (category_name) VALUES (%s) RETURNING category_id",
                (cat_name,),
            )
            category_ids[cat_name] = cur.fetchone()[0]

        products = {}  # name -> (product_id, unit_price)
        for cat_name, base_names in CATEGORY_PRODUCTS.items():
            cat_id = category_ids[cat_name]
            for base in base_names:
                variants = {base}
                if base not in ("Laptop", "Mouse"):
                    for _ in range(random.randint(0, 2)):
                        variants.add(f"{random.choice(VARIANT_PREFIXES)}{base}".strip())
                for name in variants:
                    price = round(random.uniform(5, 1500), 2)
                    stock = random.randint(0, 500)
                    cur.execute(
                        """
                        INSERT INTO ecommerce.products (product_name, category_id, unit_price, stock_quantity, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING product_id
                        """,
                        (name, cat_id, price, stock, random_date(2020, 2024)),
                    )
                    products[name] = (cur.fetchone()[0], price)

        laptop_id, laptop_price = products["Laptop"]
        mouse_id, mouse_price = products["Mouse"]
        all_product_names = list(products.keys())

        customer_ids = []
        for _ in range(NUM_CUSTOMERS):
            first, last = fake.first_name(), fake.last_name()
            email = f"{first}.{last}{random.randint(1, 999)}@example.com".lower()
            cur.execute(
                """
                INSERT INTO ecommerce.customers (first_name, last_name, email, phone, city, country, signup_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING customer_id
                """,
                (first, last, email, fake.phone_number()[:20], fake.city(), fake.country(), random_date(2019, 2024)),
            )
            customer_ids.append(cur.fetchone()[0])

        def create_order(customer_id, item_specs):
            order_date = random_date()
            status = random.choice(ORDER_STATUSES)
            cur.execute(
                "INSERT INTO ecommerce.orders (customer_id, order_date, status) VALUES (%s, %s, %s) RETURNING order_id",
                (customer_id, order_date, status),
            )
            order_id = cur.fetchone()[0]
            total = 0
            for product_id, unit_price, qty in item_specs:
                cur.execute(
                    "INSERT INTO ecommerce.order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                    (order_id, product_id, qty, unit_price),
                )
                total += float(unit_price) * qty
            cur.execute(
                """
                INSERT INTO ecommerce.payments (order_id, payment_method, amount, payment_date, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (order_id, random.choice(PAYMENT_METHODS), round(total, 2), order_date, random.choice(PAYMENT_STATUSES)),
            )

        for cid in LAPTOP_ONLY_IDS:
            create_order(customer_ids[cid - 1], [(laptop_id, laptop_price, 1)])

        for cid in LAPTOP_AND_MOUSE_IDS:
            create_order(customer_ids[cid - 1], [(laptop_id, laptop_price, 1), (mouse_id, mouse_price, 1)])

        for cid in MOUSE_ONLY_IDS:
            create_order(customer_ids[cid - 1], [(mouse_id, mouse_price, random.randint(1, 2))])

        for cid in customer_ids[45:]:
            for _ in range(random.randint(1, 6)):
                num_items = random.randint(1, 5)
                chosen = random.sample(all_product_names, num_items)
                item_specs = [
                    (products[name][0], products[name][1], random.randint(1, 3))
                    for name in chosen
                ]
                create_order(cid, item_specs)

    conn.close()
    print(f"ecommerce: seeded {len(category_ids)} categories, {len(products)} products, "
          f"{NUM_CUSTOMERS} customers, plus orders/items/payments.")


if __name__ == "__main__":
    seed()
