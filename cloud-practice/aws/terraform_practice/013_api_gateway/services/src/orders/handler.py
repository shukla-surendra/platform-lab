"""POST /orders  - developer-owned code."""
import json
import os
import uuid


def lambda_handler(event, context):
    try:
        order = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _resp(400, {"error": "body must be valid JSON"})

    if not order.get("item"):
        return _resp(400, {"error": "item is required"})

    order_id = f"{os.environ.get('ORDER_PREFIX', 'ord')}-{uuid.uuid4().hex[:8]}"
    print(f"created {order_id}: {order}")
    return _resp(201, {"order_id": order_id, "item": order["item"]})


def _resp(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}
