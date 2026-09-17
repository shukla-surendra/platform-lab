import json
import os
import time


def handler(event, context):
    """Trivial demo handler — echoes the event back with a timestamp.

    Swap this file's contents for your real logic; Terraform re-zips and
    re-deploys automatically whenever this file's content changes (see
    the archive_file data source's source_code_hash in main.tf).
    """
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": f"Hello from {os.environ.get('PROJECT', 'lambda')}",
                "received_event": event,
                "unix_time": int(time.time()),
            }
        ),
    }
