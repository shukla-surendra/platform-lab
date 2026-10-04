#!/usr/bin/env python3
"""Send dummy messages to the SQS queue.

Usage:
  python3 scripts/send_message.py --queue-url <url> --count 3
  python3 scripts/send_message.py --queue-url <url> --count 1 --fail     # poison message -> retries -> DLQ

Needs: pip install boto3 (and AWS credentials in your environment).
"""
import argparse
import json
import uuid

import boto3


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queue-url", required=True)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--fail", action="store_true", help="make the Lambda raise for these messages")
    p.add_argument("--region", default="us-east-1")
    args = p.parse_args()

    sqs = boto3.client("sqs", region_name=args.region)

    for i in range(args.count):
        body = {
            "order_id": str(uuid.uuid4())[:8],
            "customer": f"customer-{i}",
            "fail": args.fail,
        }
        resp = sqs.send_message(QueueUrl=args.queue_url, MessageBody=json.dumps(body))
        print(f"sent {body['order_id']} (MessageId {resp['MessageId']})")


if __name__ == "__main__":
    main()
