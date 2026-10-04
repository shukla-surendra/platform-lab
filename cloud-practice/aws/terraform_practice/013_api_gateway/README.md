# 013 – API Gateway (HTTP API) with two routes, two Lambdas, and a clear ownership split

Read `OWNERSHIP.md` first if your question is "what is DevOps's job and what is the developer's?". This lesson is built around that split.

Nothing here is applied automatically. What has been checked *(verified)*: `terraform validate` passes for both stacks; the Lambda handlers were run locally with sample events. **Not yet applied or called in AWS.**

## Layout = ownership

```
013_api_gateway/
├── platform/              DEVOPS owns   the API, stage, logging, throttling, CORS, published contract
├── modules/lambda_route/  DEVOPS writes, DEVELOPERS use   "one Lambda behind one route" in one block
└── services/              DEVELOPERS own   routes + Lambda code (+ function settings)
    └── src/
        ├── hello/handler.py     GET  /hello
        └── orders/handler.py    POST /orders
```

```
client ──HTTPS──▶ HTTP API (platform) ──route GET /hello──▶  Lambda hello   (developer)
                    $default stage                └─route POST /orders─▶ Lambda orders  (developer)
                    logs + throttling + CORS
```

## How the two stacks connect

The platform stack publishes two values in SSM Parameter Store (`/platform/demo-http-api/api_id` and `.../execution_arn`). The services stack reads them with `data "aws_ssm_parameter"`. No shared Terraform state, no copy-pasted IDs; separate state files, separate pipelines.

## Run it

```
# 1. Platform (once, rarely changes)
cd platform
terraform init && terraform apply

# 2. Services (developer workflow, runs often)
cd ../services
terraform init && terraform apply

# 3. Call it
terraform output                       # hello_url and orders_url
curl "$(terraform output -raw hello_url)?name=sam"
curl -X POST "$(terraform output -raw orders_url)" \
     -H 'content-type: application/json' -d '{"item":"book"}'
curl -X POST "$(terraform output -raw orders_url)" -d '{}'      # 400: item is required
curl -i "$(terraform output -raw hello_url | sed 's#/hello#/nope#')"   # 404: no such route
```

Logs: Lambda logs in `/aws/lambda/apigw-lab-hello` and `-orders`; API access logs in `/aws/apigateway/demo-http-api` (platform's log group).

## Destroy (reverse order)

```
cd services && terraform destroy     # developers' routes and functions first
cd ../platform && terraform destroy  # then the API
```
Destroying the platform first would leave service routes pointing at a deleted API.

## What a developer does to add an endpoint

1. Create `services/src/products/handler.py`.
2. Add a block to `services/main.tf`:
   ```hcl
   module "products" {
     source            = "../modules/lambda_route"
     api_id            = data.aws_ssm_parameter.api_id.value
     api_execution_arn = data.aws_ssm_parameter.execution_arn.value
     function_name     = "apigw-lab-products"
     route_key         = "GET /products"
     source_dir        = "${path.module}/src/products"
   }
   ```
3. PR -> plan reviewed -> `terraform apply` in `services/`.
4. **No ticket to the platform team and no redeploy of the API.** The stage has `auto_deploy = true`, so the new route is live as soon as it is created.

## What the module hides (so developers don't hand-write it)

Per route, `modules/lambda_route` creates: the Lambda + its own IAM role + log group, the API **integration** (`AWS_PROXY`), the **route**, and the **Lambda permission** that lets API Gateway invoke that function for that route only. Forgetting the permission is the classic cause of a route returning `500 Internal Server Error`.

## Cost (approx.; verify)

HTTP API is roughly $1 per million requests; Lambda, CloudWatch Logs and SSM standard parameters are negligible at lab volumes. A lab costs cents or less; nothing runs when idle.
