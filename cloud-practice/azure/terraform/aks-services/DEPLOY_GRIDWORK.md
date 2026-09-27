# Deploying gridwork onto This Cluster

Step-by-step record of deploying [gridwork](https://github.com/shukla-surendra/gridwork)
(FastAPI backend + Next.js/nginx frontend + Postgres + Redis) onto the
`aks-services` lab cluster, using **gridwork's own Helm chart unchanged**
(`gridwork/helm/personal-assistant`). Everything here was run for real on
2026-09-27, including the two failures and how they were fixed.

This is a lighter path than gridwork's own `AKS_DEPLOYMENT_GUIDE.md`
(which has 4 Terraform stages plus Key Vault, Workload Identity, KEDA, Front Door and
cert-manager). Here it's just: registry → images → `helm install` → a
LoadBalancer Service.

```
                    Internet
                       │  http://<public-ip>
                       ▼
     Azure LB "kubernetes"  (new frontend + public IP, same shared LB)
                       │
   ┌─────────────── namespace gridwork ───────────────────────────────┐
   │ svc/gridwork-frontend-public (LoadBalancer)   <- this module     │
   │        │                                                         │
   │        ▼                                                         │
   │ deploy/gridwork-frontend  nginx: /  → static Next.js export      │
   │        │                         /api/ → proxy                   │
   │        ▼                                                         │
   │ svc/gridwork-backend (ClusterIP :8000) → deploy/gridwork-backend │
   │        │                                        │                │
   │        ▼                                        ▼                │
   │ sts/gridwork-postgres (headless svc)      deploy/gridwork-redis  │
   │   └─ PVC 1Gi → Azure Managed Disk (StandardSSD_LRS)              │
   │ job/gridwork-migrate-N (alembic upgrade head, Helm hook)         │
   └──────────────────────────────────────────────────────────────────┘
```

## Files in this module

| File | Purpose |
|---|---|
| `main.tf` | ACR (`azurerm_container_registry.acr`) + `AcrPull` for the kubelet identity (`azurerm_role_assignment.kubelet_acr_pull`) |
| `gridwork/values-aks-services.yaml` | Helm overrides: `pullPolicy: IfNotPresent`, ingress off. **No secrets** |
| `gridwork/frontend-lb.yaml` | Extra `type: LoadBalancer` Service for the frontend pods |

## Step 1: Registry and pull permission (Terraform)

```bash
cd cloud-practice/azure/terraform/aks-services
terraform apply
terraform output acr_login_server      # akssvc<suffix>acr.azurecr.io
```

- **ACR Basic** (~US$0.17/day), admin user disabled.
- **`AcrPull` → the kubelet identity** (`<cluster>-agentpool` in the `MC_` group).
  The kubelet on the node pulls images, not the cluster's control-plane
  identity. This is what `az aks update --attach-acr` does. It's kept in
  Terraform here so `destroy` removes it too.
- `upgrade_settings { max_surge = "10%" }` was also added to the node pool.
  It stops a perpetual "1 to change" diff (AKS sets that value server-side).

## Step 2: Build and push the images

### Build from `git archive`, not the working tree

```bash
TAG=$(git -C ~/projects/2026/gridwork rev-parse --short HEAD)   # 166f8cf
SRC=$(mktemp -d)
git -C ~/projects/2026/gridwork archive $TAG assistant_backend assistant_web | tar -x -C $SRC
```

Why: `assistant_backend/` has **no `.dockerignore`**, a gitignored local `.env`, and a Dockerfile that does `COPY . .`.
Building from the working tree would **bake your local `.env` into the
image** and push it to the registry. `git archive` contains only committed files,
and the image then matches the tag exactly. (`assistant_web/.dockerignore`
already excludes `.env`, `node_modules`, `.next` and `out`.)

### `az acr build` doesn't work on this subscription

```
$ az acr build -r <acr> -t gridwork-backend:$TAG --platform linux/amd64 $SRC/assistant_backend
Code: TasksOperationsNotAllowed
Message: ACR Tasks requests for the registry ... are not permitted.
```

ACR Tasks (building in the cloud) is disabled for free/trial subscriptions,
and only a support request can enable it. So: build locally.

### Local cross-arch build + push

The Mac is **arm64**, the AKS node is **amd64**, so `--platform linux/amd64`
is required. Without it, the pod fails with `exec format error`. It runs under
QEMU emulation, so expect several minutes, mostly for `npm ci` / `pip install`.

```bash
R=$(terraform output -raw acr_login_server)
az acr login -n $(terraform output -raw acr_name)

docker buildx build --platform linux/amd64 -t $R/gridwork-backend:$TAG  --push $SRC/assistant_backend
docker buildx build --platform linux/amd64 -t $R/gridwork-frontend:$TAG --push $SRC/assistant_web

az acr repository show-tags -n $(terraform output -raw acr_name) --repository gridwork-backend -o tsv
```

## Step 3: `helm install`

```bash
helm upgrade --install gridwork ~/projects/2026/gridwork/helm/personal-assistant \
  -n gridwork --create-namespace \
  -f gridwork/values-aks-services.yaml \
  --set backend.image.repository=$R/gridwork-backend   --set backend.image.tag=$TAG \
  --set frontend.image.repository=$R/gridwork-frontend --set frontend.image.tag=$TAG \
  --set secrets.postgresPassword=$(openssl rand -hex 16) \
  --set secrets.jwtSecret=$(openssl rand -hex 32) \
  --wait --timeout 10m
```

What the chart creates (release name `gridwork` becomes the name prefix):

| Object | Notes |
|---|---|
| `deploy/gridwork-backend` + `svc` ClusterIP :8000 | FastAPI. Probes on `/health` |
| `deploy/gridwork-frontend` + `svc` **NodePort** :80 | nginx serving the static export and proxying `/api/` → backend |
| `sts/gridwork-postgres` + headless `svc` | `postgres:15`, PVC `data-gridwork-postgres-0` (1 Gi) |
| `deploy/gridwork-redis` + `svc` | `redis:7` |
| `secret/gridwork-secrets` | `POSTGRES_PASSWORD`, `JWT_SECRET`, `OPENAI_API_KEY` (empty, so chat returns 503 by design) |
| `job/gridwork-migrate-<revision>` | `alembic upgrade head`. Helm hook: **post-install**, pre-upgrade |
| `sa/gridwork-backend`, configmap | |

### ❌ Failure 1: backend `CrashLoopBackOff`, `No module named 'psycopg'`

```
File "/app/adapters/orm/models/database.py", line 24, in create_db_engine
  ...sqlalchemy/dialects/postgresql/psycopg.py ... import psycopg
ModuleNotFoundError: No module named 'psycopg'
```

Root cause: a **real gridwork bug that only shows up on a fresh build**.

- `requirements.txt` has `sqlalchemy>=1.4.23` (unpinned upper bound) and `psycopg2-binary==2.9.9`.
- A fresh build resolved **SQLAlchemy 2.1.1** (`pip show sqlalchemy` inside the image).
- In SQLAlchemy 2.1, a plain `postgresql://` URL (which `config.py`'s `database_url`
  builds) defaults to the **psycopg 3** driver, not psycopg2. psycopg 3 isn't installed.
- Older local images work because they were built when pip resolved to 2.0.x.

Because the backend Deployment never became ready, `--wait` timed out, the
release was marked **failed** and the **post-install migration hook never ran**.

**Workaround used here** (in the build copy only, gridwork repo untouched):

```bash
sed -i '' 's|^sqlalchemy>=1.4.23|sqlalchemy>=1.4.23,<2.1|' $SRC/assistant_backend/requirements.txt
docker buildx build --platform linux/amd64 -t $R/gridwork-backend:$TAG-sqla20 --push $SRC/assistant_backend
```

The distinct tag `166f8cf-sqla20` makes it clear this image is **not**
exactly commit `166f8cf`.

**Proper fix belongs in gridwork**. Either:
- pin `sqlalchemy>=2.0,<2.1` in `requirements.txt`, or
- make the driver explicit: `postgresql+psycopg2://...` in `config.py` (works on 1.4, 2.0 and 2.1), or
- switch to `psycopg[binary]` (v3) and keep the plain URL.

### Re-deploy with the fixed image, reusing the same secrets

⚠️ **Don't generate new passwords on the upgrade.** Postgres initialized its data
volume with the first password, so a new `POSTGRES_PASSWORD` would stop the backend
authenticating. Read the existing values back:

```bash
PGPW=$(kubectl get secret gridwork-secrets -n gridwork -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)
JWT=$(kubectl get secret gridwork-secrets -n gridwork -o jsonpath='{.data.JWT_SECRET}' | base64 -d)

helm upgrade --install gridwork ~/projects/2026/gridwork/helm/personal-assistant \
  -n gridwork -f gridwork/values-aks-services.yaml \
  --set backend.image.repository=$R/gridwork-backend   --set backend.image.tag=$TAG-sqla20 \
  --set frontend.image.repository=$R/gridwork-frontend --set frontend.image.tag=$TAG \
  --set secrets.postgresPassword="$PGPW" --set secrets.jwtSecret="$JWT" \
  --wait --timeout 8m
```

The upgrade triggers the **pre-upgrade** hook, so `job/gridwork-migrate-2` runs
all Alembic migrations (the ones install skipped) with the fixed image
*before* the backend rolls out:

```
job.batch/gridwork-migrate-2   Complete   1/1   21s
INFO  [alembic.runtime.migration] Running upgrade ... -> d8f3b6c15a2e, add crm leads and deal quote_id
```

## Step 4: Expose the frontend with a LoadBalancer Service

The chart makes the frontend a `NodePort` (its minikube default when
ingress is off). A NodePort isn't reachable from the internet on AKS
(the NSG blocks it and nodes have no public IPs). Rather than editing the chart, add a
**second Service selecting the same pods**:

```bash
kubectl apply -f gridwork/frontend-lb.yaml
kubectl get svc -n gridwork gridwork-frontend-public -w     # wait for EXTERNAL-IP
```

```
gridwork-backend           ClusterIP      10.0.162.81    <none>          8000/TCP
gridwork-frontend          NodePort       10.0.212.134   <none>          80:30932/TCP
gridwork-frontend-public   LoadBalancer   10.0.174.219   98.70.243.116   80:30757/TCP
gridwork-postgres          ClusterIP      None           <none>          5432/TCP
gridwork-redis             ClusterIP      10.0.138.6     <none>          6379/TCP
```

Same behavior as the experiment in [`README.md`](README.md): **no new Azure
Load Balancer**. The shared `kubernetes` LB went from 1 to 2 frontends
(outbound + this Service).

## Step 5: Verify end to end

```bash
IP=$(kubectl get svc gridwork-frontend-public -n gridwork -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

curl -s -o /dev/null -w '%{http_code}\n' http://$IP/                      # 200: the UI
kubectl exec -n gridwork deploy/gridwork-frontend -- wget -qO- http://gridwork-backend:8000/health
# {"status":"healthy","version":"1.0.0","environment":"development","database":"healthy"}
curl -s http://$IP/api/v1/workspaces/                                     # 403 "Could not validate credentials"
```

A full round trip (browser path → nginx → backend → Postgres):

```bash
curl -X POST http://$IP/api/v1/users/signup -H 'Content-Type: application/json' \
  -d '{"first_name":"Lab","last_name":"Test","email":"labtest@example.com","password":"<pw>"}'   # 201
curl -X POST http://$IP/api/v1/users/login  -H 'Content-Type: application/json' \
  -d '{"email":"labtest@example.com","password":"<pw>"}'                                          # access_token
curl http://$IP/api/v1/workspaces/member-workspaces -H "Authorization: Bearer <token>"             # 200
kubectl exec -n gridwork gridwork-postgres-0 -- \
  psql -U postgres -d productify -tAc "select count(*) from users where email='labtest@example.com'"  # 1
```

Notes:
- `/health` is at the backend's **root**, not under `/api/`. nginx only proxies
  `/api/*` (to `backend:8000/api/*`), so `http://$IP/api/health` → 404 from FastAPI.
  That's expected, and it does prove the proxy works.
- Open `http://<IP>/` in a browser. It's plain HTTP (no TLS, no domain).

## What this added in Azure

| Resource | Where | Created by |
|---|---|---|
| `akssvc<suffix>acr` Container Registry (Basic) | `rg-aks-services-demo` | Terraform |
| `AcrPull` role assignment → kubelet identity | on the ACR | Terraform |
| Managed Disk `pvc-<uid>` (1 GiB, StandardSSD_LRS, tag `kubernetes.io-created-for-pvc-name=data-gridwork-postgres-0`) | `MC_...` | Azure Disk CSI driver (from the PVC) |
| Public IP `kubernetes-a<uid>` + frontend/rule/probe on the `kubernetes` LB + NSG allow rule | `MC_...` | cloud-controller-manager (from `gridwork-frontend-public`) |

See [`AZURE_RESOURCES.md`](AZURE_RESOURCES.md) for the baseline inventory.

## Shipping a new gridwork version

```bash
TAG=$(git -C ~/projects/2026/gridwork rev-parse --short HEAD)
# git archive → buildx --platform linux/amd64 --push (Step 2), then:
helm upgrade gridwork ~/projects/2026/gridwork/helm/personal-assistant -n gridwork \
  -f gridwork/values-aks-services.yaml --reuse-values \
  --set backend.image.tag=$TAG --set frontend.image.tag=$TAG --wait
```

`--reuse-values` keeps the image repositories and secrets from the previous
revision. The pre-upgrade hook runs any new migrations first.

## Tear down

```bash
kubectl delete -f gridwork/frontend-lb.yaml          # releases the public IP cleanly
helm uninstall gridwork -n gridwork
kubectl delete pvc -n gridwork --all                  # StatefulSet PVCs survive uninstall -> would keep the Azure Disk
kubectl delete ns gridwork
terraform destroy                                     # cluster, MC_ group, ACR + images
```

The PVC step matters. Helm does **not** delete StatefulSet `volumeClaimTemplates`
PVCs, so the Azure Managed Disk (and its cost) would otherwise stay until
the whole cluster is destroyed.
