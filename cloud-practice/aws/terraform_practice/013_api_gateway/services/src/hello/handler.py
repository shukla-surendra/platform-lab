"""GET /hello  - developer-owned code. Event format: API Gateway HTTP API payload v2.0."""
import json


def lambda_handler(event, context):
    name = (event.get("queryStringParameters") or {}).get("name", "world")
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"message": f"hello, {name}"}),
    }
