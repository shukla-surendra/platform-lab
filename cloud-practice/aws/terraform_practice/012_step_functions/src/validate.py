"""Step 1 of the workflow: validate the order. Input is the execution input."""


def lambda_handler(event, context):
    errors = []
    if not event.get("order_id"):
        errors.append("order_id missing")
    if not isinstance(event.get("amount"), (int, float)) or event["amount"] <= 0:
        errors.append("amount must be a positive number")

    result = {"valid": not errors, "errors": errors}
    print(f"validate: {result}")
    return result
