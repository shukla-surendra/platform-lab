# Terraform + Code: Azure RBAC Least-Privilege, End to End (AWS IAM → Azure RBAC)

A real Azure Function (Python) that downloads a CSV from one Blob
container, computes a total, and uploads the result to a second
container — authenticating with nothing but its own Managed Identity, no
key or connection string anywhere. Two custom RBAC roles, each scoped to
exactly one container, are the *entire* reason it can do exactly that and
nothing more — verified live below, including the denial when the code
deliberately steps outside them.

> ⚠️ **This creates billable, continuously-running resources** — a
> Function App (Consumption plan; cheap, pay-per-execution) and two
> Storage Accounts. Role definitions/assignments themselves aren't
> billed. Run `terraform destroy` when done.

This doc focuses on the identity/permissions axis specifically. For the
broader "coming from Lambda" picture — why Azure even makes you pick a
Service Plan, Triggers vs. Bindings, packaging/deployment differences,
execution limits side by side — see
[`../functions/AWS_LAMBDA_CONTRAST.md`](../functions/AWS_LAMBDA_CONTRAST.md).

## The AWS → Azure translation, concept by concept

Coming from AWS IAM, the vocabulary doesn't map 1:1 — Azure splits two
things AWS bundles into one:

| AWS IAM | Azure RBAC | The actual difference |
|---|---|---|
| **IAM Policy document** (JSON: `Effect`/`Action`/`Resource`/`Condition`) | **Role Definition** (`azurerm_role_definition` — `actions`/`data_actions`/`not_actions`/`assignable_scopes`) | Same idea (a named, reusable allow-list), but Azure splits the allow-list itself into two arrays — see below. |
| **IAM Role** (trust policy *and* attached policies, one resource) | **Managed Identity** + **Role Assignment**, two *separate* resource types | This is the mental-model shift that matters most. AWS bundles "who this compute assumes as" and "what that identity can do" into one Role. Azure splits them: the Function App's `identity { type = "SystemAssigned" }` block (this module's `main.tf`) is purely *who* — Azure auto-creates and rotates a service principal for it, nothing about permissions yet. A `azurerm_role_assignment` is a completely separate resource that says *what* — bind one Role Definition to one principal at one scope. You can create the identity with zero role assignments (an identity that can do literally nothing) or assign the same Role Definition to five different identities — they vary completely independently. |
| **Resource ARN** in a policy's `Resource` field | **`scope`** (a property of the assignment, constrained by the definition's `assignable_scopes`) | AWS scoping is flat: one ARN pattern, however deep. Azure scoping is a real hierarchy — Management Group → Subscription → Resource Group → Resource → **sub-resource** (this module scopes all the way down to one Blob **container**, not just the storage account). |
| **`s3:GetObject`, `s3:PutObject`** (plain Action strings) | **`Actions`** (control/management-plane) vs **`DataActions`** (actual data-plane operations) — two different arrays in the same Role Definition | AWS doesn't force this split explicitly. Azure does: `Microsoft.Storage/storageAccounts/read` (an `Actions` entry — can you see this resource exists in ARM) is a completely different kind of permission from `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read` (a `DataActions` entry — can you actually read blob *content*). Grant the wrong array and the permission silently doesn't apply — confirmed the hard way below. |
| **Instance profile / Lambda execution role** supplying temporary credentials automatically (via IMDS / Lambda's runtime) | **Managed Identity** supplying an AAD token automatically (via the sandboxed `IDENTITY_ENDPOINT`, wrapped by `DefaultAzureCredential()` in code) | Mechanically the same idea — code never sees a long-lived secret, the platform hands it a short-lived token transparently. This module's `function_app.py` never touches a key; `DefaultAzureCredential()` is doing the exact job an EC2/Lambda SDK call to the metadata service does. |

## What this module actually builds

```
Function App (SystemAssigned Managed Identity)
 │
 ├─ Role Assignment ──> "Blob Reader (input only)"  ──scope──> data-storage/input container
 │                        data_actions: [blobs/read]
 │
 └─ Role Assignment ──> "Blob Writer (output only)" ──scope──> data-storage/output container
                          data_actions: [blobs/write, blobs/add/action]
```

Two Role Definitions, mirroring writing two separate IAM policy
statements — one read-only on `input/*`, one write-only on `output/*` —
except here they're two independent, separately-scoped Azure resources,
each individually assignable, reusable, and revocable.

## Usage

```bash
cd cloud-practice/azure/terraform/function-storage-rbac
terraform init
terraform apply
```

## Deploying the function code

Azure Functions on Linux Consumption defaults to **"Run From Package"**
mode (`WEBSITE_RUN_FROM_PACKAGE` gets set to a SAS URL pointing at an
immutable zip in the runtime storage account) — and that mode has **no
remote build step**. `SCM_DO_BUILD_DURING_DEPLOYMENT=true` only matters
for the *other* deploy path; in Run-From-Package mode it's silently
ignored. Hit this directly: a zip with just `function_app.py` +
`requirements.txt` deployed cleanly (`az` reported success) but
`azure.functions`/`azure.identity`/`azure.storage.blob` were never
installed, so the Python worker failed to import the module and **every
route 404'd with zero functions ever registered** — no error surfaced
anywhere in the CLI output. The fix is to vendor dependencies *inside*
the zip yourself (what `func azure functionapp publish` does for you
normally):

```bash
cd function_app
python3 -m pip install \
  --target=.python_packages/lib/site-packages \
  --platform manylinux2014_x86_64 --implementation cp \
  --python-version 3.11 --only-binary=:all: --upgrade \
  -r requirements.txt

zip -r ../function_app.zip . -x "*.pyc" -x "__pycache__/*"
cd ..

az functionapp deployment source config-zip \
  --resource-group "$(terraform output -raw resource_group_name)" \
  --name "$(terraform output -raw function_app_name)" \
  --src function_app.zip
```

(`.python_packages/` and `function_app.zip` are gitignored — regenerate
them with the commands above, don't commit vendored platform-specific
wheels.)

## Verify: the authorized path works

```bash
HOST=$(terraform output -raw default_hostname)
curl "https://$HOST/api/process"
```

Actual output from this exact deployment:

```json
{"rows_processed": 3, "total": 69.74, "read_from": "input/sample.csv", "wrote_to": "output/sample.csv"}
```

Confirm the file really landed (using your own broader credentials, not
the function's — the function itself can't read this container back):

```bash
SA=$(terraform output -raw data_storage_account_name)
KEY=$(az storage account keys list --account-name "$SA" --query "[0].value" -o tsv)
az storage blob download --account-name "$SA" --account-key "$KEY" \
  --container-name output --name sample.csv --file /tmp/result.csv
cat /tmp/result.csv
```

```
order_id,status,amount
1,pending,42.50
2,shipped,19.99
3,pending,7.25

# total,,69.74
```

## Verify: least privilege actually holds, from inside the running code

```bash
curl "https://$HOST/api/violate"
```

Actual output — both attempts denied by Azure RBAC itself, not by
anything the code chose to forbid:

```json
{
  "write_to_input_container": "DENIED - status=403 error_code=AuthorizationPermissionMismatch",
  "read_from_output_container": "DENIED - status=403 error_code=AuthorizationPermissionMismatch"
}
```

The reader role's `data_actions` never included `blobs/write`; the
writer role's `data_actions` never included `blobs/read`. Same identity,
same code, same running process — one call succeeds, the other two fail,
purely because of which `DataActions` are listed on which Role
Definition at which scope. This is the AWS-IAM-policy-testing workflow
(deploy a Lambda with a narrow execution role, try an action outside it,
watch `AccessDenied`) reproduced exactly, on Azure's primitives instead.

## The `Actions` vs `DataActions` gotcha, confirmed against the real API

Building the reader role, `Microsoft.Storage/storageAccounts/blobServices/containers/read`
seemed like the obvious "list what's in this container" permission to
pair with blob-level read. Azure rejected it outright:

```
Error: unexpected status 400 (400 Bad Request) with error:
InvalidDataActionOrNotDataAction: 'Microsoft.Storage/storageAccounts/blobServices/containers/read'
does not match any of the actions supported by the providers.
```

Checked which operations are *actually* flagged as data-plane against the
live provider (not from memory/docs — from the API itself):

```bash
az provider operation show --namespace Microsoft.Storage \
  --query "resourceTypes[?name=='storageAccounts/blobServices/containers'].operations[].{name:name, isDataAction:isDataAction}" \
  -o table
```

Every `containers/*` operation (`read`, `write`, `delete`, `setAcl/action`, ...)
comes back `isDataAction: False` — they're regular ARM control-plane
`Actions`, despite being served by what feels like "the data path."
**Only `containers/blobs/*` operations are true `DataActions`** (`read`,
`write`, `delete`, `add/action`, `move/action`, ...). Azure's line between
"control plane" and "data plane" for Storage isn't always where it
looks like it should be from the resource path alone — this module's
reader role ended up with just `blobs/read`, nothing at the container
level, because container-level listing genuinely isn't a `DataAction`
this API supports granting narrowly at all.

## Where this stops mapping cleanly to AWS: prefix-level scoping

AWS IAM can scope a policy to a key *prefix* inside a bucket
(`arn:aws:s3:::bucket/input/*`) with a plain `Resource` pattern. Azure
RBAC's `scope` only goes as granular as a **container** (what this module
does) — there's no equivalent of "this role, but only for blobs whose
name starts with `2026/`" using `scope` alone. The closer analog is Azure
ABAC: **conditions** attached to a role assignment
(`azurerm_role_assignment.condition`) that filter by blob path/tags at
evaluation time, layered on top of an RBAC role rather than replacing it
— genuinely a different mechanism from AWS's inline `Resource`/`Condition`
pattern-matching, not just different syntax for the same idea. Not used
here (container-level scoping was granular enough for this demo) but the
right next thing to explore if you need prefix-level control within one
container.

## What's deliberately not here

No delete permission anywhere (neither role includes a `blobs/delete`
`data_action` — this workload only ever needs to read and write). No
Managed Identity on the function's *own* runtime storage account (that
one still uses a key, same as the plain `functions/` module in this
repo — deliberately kept "boring" so the least-privilege story stays
about the data account only). No Azure AD app registration / service
principal with a client secret anywhere — System-Assigned Managed
Identity only. No custom domain / VNet integration / private endpoints
(this Function App is publicly reachable at its default hostname, fine
for a demo, not for a production data-processing workload).

## Teardown

```bash
terraform destroy
```
