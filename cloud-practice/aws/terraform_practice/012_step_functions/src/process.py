"""Step 2 of the workflow: process the order.

Demo failure switches (set "simulate" in the execution input):
  "transient" -> raises TransientError  (workflow retries with backoff, then fails)
  "fatal"     -> raises ValueError      (workflow goes straight to the Catch)
The exception CLASS NAME becomes the Step Functions error name, which is what
"ErrorEquals" in the ASL matches on.
"""


class TransientError(Exception):
    pass


def lambda_handler(event, context):
    mode = event.get("simulate")
    if mode == "transient":
        raise TransientError("temporary problem, safe to retry")
    if mode == "fatal":
        raise ValueError("permanent problem, retrying will not help")

    print(f"processed order {event['order_id']} amount {event['amount']}")
    return {"status": "PROCESSED", "order_id": event["order_id"]}
