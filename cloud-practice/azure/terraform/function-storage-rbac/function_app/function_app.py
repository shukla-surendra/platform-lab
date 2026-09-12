"""Two HTTP-triggered functions that prove least-privilege RBAC from the
inside, not just on paper.

Authentication: no key, no connection string, anywhere in this file.
DefaultAzureCredential(), running inside a real Azure Function, resolves
to the Function App's own system-assigned Managed Identity -- the token
it gets back is only ever as powerful as the custom roles Terraform bound
to that identity (see main.tf).

- /api/process : the intended, authorized workflow -- download a CSV from
  the 'input' container, compute a total, upload the result to 'output'.
- /api/violate : deliberately attempts two actions the assigned roles do
  NOT grant, and reports the real Azure RBAC denial for each.
"""

import csv
import io
import json
import os

import azure.functions as func
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

ACCOUNT = os.environ["DATA_STORAGE_ACCOUNT_NAME"]
INPUT_CONTAINER = os.environ.get("INPUT_CONTAINER", "input")
OUTPUT_CONTAINER = os.environ.get("OUTPUT_CONTAINER", "output")


def _blob_service() -> BlobServiceClient:
    credential = DefaultAzureCredential()
    return BlobServiceClient(
        account_url=f"https://{ACCOUNT}.blob.core.windows.net",
        credential=credential,
    )


@app.route(route="process", methods=["GET", "POST"])
def process(req: func.HttpRequest) -> func.HttpResponse:
    blob_name = req.params.get("blob", "sample.csv")
    service = _blob_service()

    raw = service.get_blob_client(container=INPUT_CONTAINER, blob=blob_name).download_blob().readall()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    rows = list(reader)
    total = sum(float(r["amount"]) for r in rows)

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    out.write(f"\n# total,,{total}\n")

    service.get_blob_client(container=OUTPUT_CONTAINER, blob=blob_name).upload_blob(
        out.getvalue(), overwrite=True
    )

    return func.HttpResponse(
        json.dumps({
            "rows_processed": len(rows),
            "total": total,
            "read_from": f"{INPUT_CONTAINER}/{blob_name}",
            "wrote_to": f"{OUTPUT_CONTAINER}/{blob_name}",
        }),
        mimetype="application/json",
    )


@app.route(route="violate", methods=["GET"])
def violate(req: func.HttpRequest) -> func.HttpResponse:
    service = _blob_service()
    results = {}

    # The reader role's data_actions on 'input' are read-only (blob read +
    # container read) -- writing should be denied by Azure RBAC itself,
    # not by anything this code chooses to forbid.
    try:
        service.get_blob_client(container=INPUT_CONTAINER, blob="should-fail.txt").upload_blob(
            b"this write should be denied by RBAC", overwrite=True
        )
        results["write_to_input_container"] = "UNEXPECTEDLY SUCCEEDED"
    except HttpResponseError as e:
        results["write_to_input_container"] = f"DENIED - status={e.status_code} error_code={e.error_code}"

    # The writer role's data_actions on 'output' are write-only -- no
    # blob-read data_action was granted there at all.
    try:
        service.get_blob_client(container=OUTPUT_CONTAINER, blob="sample.csv").download_blob().readall()
        results["read_from_output_container"] = "UNEXPECTEDLY SUCCEEDED"
    except HttpResponseError as e:
        results["read_from_output_container"] = f"DENIED - status={e.status_code} error_code={e.error_code}"

    return func.HttpResponse(json.dumps(results, indent=2), mimetype="application/json")
