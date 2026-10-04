"""Lambda that processes SQS messages.

SQS invokes this with a BATCH of messages:
    {"Records": [{"messageId": "...", "body": "...", ...}, ...]}

Return {"batchItemFailures": [{"itemIdentifier": id}, ...]} to say which
messages failed; only those go back to the queue (then to the DLQ after
max_receive_count attempts). Return an empty list = all succeeded = batch deleted.
"""
import json


def process(body: dict) -> None:
    """Your business logic. Demo: raise if the message asks to fail."""
    if body.get("fail"):
        raise ValueError(f"asked to fail: {body}")
    print(f"processed order {body.get('order_id')} for {body.get('customer')}")


def lambda_handler(event, context):
    failures = []

    for record in event["Records"]:
        message_id = record["messageId"]
        try:
            body = json.loads(record["body"])
            process(body)
        except Exception as exc:  # noqa: BLE001 - report any error for this message
            print(f"FAILED message {message_id}: {exc}")
            failures.append({"itemIdentifier": message_id})

    print(f"batch of {len(event['Records'])}: {len(failures)} failed")
    return {"batchItemFailures": failures}
