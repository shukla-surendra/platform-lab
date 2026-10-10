# Connecting Airflow to AWS

Operator/hook imports, secrets-backend class paths, connection URI format and logging setting
names below were checked against `apache-airflow-providers-amazon` 9.12.0 on Airflow 3.0.6.
Nothing was run against a real AWS account, and I did not start the Docker stack.

## 1. How it fits together

```
DAG task ──> Operator / Hook (provider code) ──> Connection "aws_default" ──> boto3 ──> AWS API
                                                  (how to authenticate)
```

- The **provider** `apache-airflow-providers-amazon` adds the AWS operators, hooks and sensors.
- A **Connection** (type `aws`) says *how to authenticate*. Tasks refer to it by id: `aws_conn_id="aws_default"`.
- Underneath it is plain **boto3**. If the connection has no credentials, boto3 uses its normal
  lookup chain (environment variables, `~/.aws` profile, instance/task role).

## 2. Step 0: is the provider installed?

```bash
docker compose exec airflow-scheduler airflow providers list | grep amazon
```

If it is missing, add it for local testing only:

```yaml
# docker-compose.yaml, under environment:
_PIP_ADDITIONAL_REQUIREMENTS: apache-airflow-providers-amazon
```

This reinstalls on every container start. For anything shared, build an image instead:

```dockerfile
FROM apache/airflow:3.0.6
RUN pip install --no-cache-dir apache-airflow-providers-amazon
```

## 3. Authentication options (best to worst)

| # | Method | Where | Secrets stored? |
|---|---|---|---|
| 1 | **IAM role of the machine** (EC2 instance profile, EKS IRSA, ECS task role, MWAA execution role) | Real deployments | None. Best. |
| 2 | **Assume a role** (`role_arn` in the connection) from base credentials | Cross-account access | Base creds only |
| 3 | **Local AWS CLI profile** mounted into the container | Local lab (including SSO) | On your laptop only |
| 4 | **Static access key + secret in the connection** | Quick tests | Yes. Avoid. |

Rule: **never put access keys in `docker-compose.yaml`, DAG files, or Git.**

### Option 1: IAM role (production)

Attach a role to wherever Airflow runs, create a connection with no credentials, and boto3 picks
the role up automatically.

```bash
airflow connections add aws_default --conn-type aws --conn-extra '{"region_name": "us-east-1"}'
```

### Option 2: assume a role

```bash
airflow connections add aws_default --conn-type aws \
  --conn-extra '{"region_name": "us-east-1", "role_arn": "arn:aws:iam::<ACCOUNT_ID>:role/airflow-data-role"}'
```

The base identity (machine role or profile) needs `sts:AssumeRole` on that role, and the role's
trust policy must allow it.

### Option 3: your local AWS CLI profile (best for this lab)

1. On your Mac, log in with the usual method (`aws configure`, or `aws sso login --profile myprofile`).
2. In `docker-compose.yaml`, uncomment these lines (they are already in the file):
   ```yaml
   AWS_PROFILE: default            # or your profile name
   AWS_DEFAULT_REGION: us-east-1
   ...
   - ~/.aws:/home/airflow/.aws:ro  # read-only mount
   ```
3. Create a connection with no credentials so boto3 uses that profile:
   ```bash
   docker compose exec airflow-scheduler airflow connections add aws_default \
     --conn-type aws --conn-extra '{"region_name": "us-east-1"}'
   ```
4. Restart: `docker compose up -d`.

SSO tokens expire. When tasks start failing with expired-token errors, run `aws sso login` on the
Mac again. The mount is read-only, and I have not confirmed that every SSO setup works read-only,
so if refresh fails, drop `:ro`.

### Option 4: static keys (avoid)

If you must, supply it through the environment instead of the UI, from a git-ignored `.env` file:

```bash
# .env  (already git-ignored)
AIRFLOW_CONN_AWS_DEFAULT='aws://<ACCESS_KEY_ID>:<URL_ENCODED_SECRET>@/?region_name=us-east-1'
```

The secret must be URL-encoded (`/` becomes `%2F`, `+` becomes `%2B`). Then uncomment
`AIRFLOW_CONN_AWS_DEFAULT: ${AIRFLOW_CONN_AWS_DEFAULT:-}` in the compose file. Prefer short-lived,
rotated keys for a dedicated IAM user with minimal permissions.

## 4. Creating the connection

Three equivalent ways:

| Way | Example |
|---|---|
| **UI** | Admin → Connections → `+` → type "Amazon Web Services", id `aws_default`, extra `{"region_name": "us-east-1"}` |
| **CLI** | `airflow connections add aws_default --conn-type aws --conn-extra '{...}'` |
| **Environment variable** | `AIRFLOW_CONN_AWS_DEFAULT='aws:///?region_name=us-east-1'` (id is the part after `AIRFLOW_CONN_`, lowercased) |

Useful `extra` keys: `region_name`, `role_arn`, `profile_name`, `endpoint_url` (for LocalStack or custom endpoints).

Verify: run lesson 7 (section 7), or in Python inside the scheduler container:

```bash
docker compose exec airflow-scheduler python -c "
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
print(AwsBaseHook(aws_conn_id='aws_default', client_type='sts').get_client_type().get_caller_identity())"
```

`airflow connections test` exists, but Airflow ships with it disabled (`[core] test_connection = Disabled`).

## 5. Least-privilege IAM for the S3 lesson

Replace the bucket name. Attach to the role or user Airflow uses.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::my-airflow-lab-bucket/airflow-lab/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::my-airflow-lab-bucket",
      "Condition": { "StringLike": { "s3:prefix": "airflow-lab/*" } }
    }
  ]
}
```

`ListBucket` is needed for the sensor (it checks the key exists). A "403" from a sensor usually
means this statement is missing.

## 6. What you can use from DAGs

| Service | Typical class (all under `airflow.providers.amazon.aws`) |
|---|---|
| S3 | `hooks.s3.S3Hook`, `operators.s3.S3CreateObjectOperator`, `sensors.s3.S3KeySensor` |
| Athena | `operators.athena.AthenaOperator` |
| Glue | `operators.glue.GlueJobOperator` |
| EMR | `operators.emr.EmrAddStepsOperator` and related |
| Lambda | `operators.lambda_function.LambdaInvokeFunctionOperator` |
| ECS | `operators.ecs.EcsRunTaskOperator` |
| Redshift, Batch, SageMaker, SQS, SNS, Step Functions | matching modules in the provider |

Pattern: Airflow *starts* the job (Glue, EMR, Athena, ECS) and waits for it. The processing
happens in AWS, not inside Airflow. Many operators accept `deferrable=True` so waiting doesn't hold a worker slot.

## 7. Lesson 7: `dags/07_aws_s3.py`

Writes an object, waits for it with a sensor, and reads it back.

1. Create a bucket you can write to, or reuse one. Example: `aws s3 mb s3://my-airflow-lab-bucket`
   (bucket names are global, so choose your own).
2. Set up the connection (section 3, option 3 is the easiest locally).
3. Trigger the DAG and set the `bucket` param to your bucket.
4. Check: `aws s3 ls s3://<your-bucket>/airflow-lab/ --recursive`.

The three task types in the DAG show the three ways to use the provider: an **operator** (do an
action), a **sensor** (wait for a condition), and a **hook** inside `@task` (custom Python logic).

## 8. Secrets: do not store them in Airflow's database in production

Point Airflow at AWS Secrets Manager or SSM Parameter Store. Connections and variables are then
looked up there on demand.

```bash
AIRFLOW__SECRETS__BACKEND=airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
AIRFLOW__SECRETS__BACKEND_KWARGS='{"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "region_name": "us-east-1"}'
```

With that, a secret named `airflow/connections/my_db` holding a connection URI becomes the
connection `my_db`. For Parameter Store use `...secrets.systems_manager.SystemsManagerParameterStoreBackend`.
The role Airflow runs as needs `secretsmanager:GetSecretValue` on those names.

## 9. Task logs in S3

Local disk logs vanish when a container or pod is replaced. Send them to S3:

```bash
AIRFLOW__LOGGING__REMOTE_LOGGING=True
AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER=s3://my-airflow-lab-bucket/airflow-logs
AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID=aws_default
```

The role needs write access to that prefix, and read access for the UI to display old logs.

## 10. Running Airflow itself on AWS

| Option | What it is | Effort | Notes |
|---|---|---|---|
| **MWAA** (Managed Workflows for Apache Airflow) | AWS-managed Airflow | Lowest | DAGs come from an S3 bucket; execution role is an IAM role; versions can lag upstream. |
| **EKS + official Helm chart** | Airflow on Kubernetes | High | Use IRSA for roles, git-sync or an image for DAGs, KubernetesExecutor or Celery. |
| **ECS/Fargate** | Containers without managing servers | Medium–high | Task roles supply credentials. |
| **EC2 + Docker Compose** | This lab on a VM | Medium | Instance profile gives credentials. Good for a small team, not for large scale. |

Terraform fits here: it creates the infrastructure (VPC, IAM roles, S3 bucket for DAGs and logs,
RDS for the metadata DB, or an MWAA environment), and your CI delivers DAG files to the bucket.
See [DEPLOYMENT.md](DEPLOYMENT.md) for the delivery models.

## 11. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ModuleNotFoundError: airflow.providers.amazon` | Provider not installed (section 2). |
| `Unable to locate credentials` | Connection has no creds and the container has no profile or role. Check the mount and `AWS_PROFILE`. |
| `ExpiredToken` / `The security token included in the request is expired` | SSO or temporary credentials expired. Log in again. |
| `AccessDenied` / 403 | IAM policy missing an action. `s3:ListBucket` is the usual one for sensors. |
| `The specified bucket does not exist` / 404 | Wrong name or region. Check `region_name` in the connection. |
| `NoSuchKey` in the read task | The key templated differently than the write task. Both use `{{ ds }}`, so check the run date. |
| Sensor times out | Wrong key or prefix, or the role cannot list the bucket. |
| Works locally, fails on the server | Local used your profile; the server's role has fewer permissions. |
