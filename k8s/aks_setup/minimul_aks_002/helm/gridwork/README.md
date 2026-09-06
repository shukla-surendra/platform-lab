# personal-assistant Helm chart

Backend (FastAPI) + frontend (Next.js/nginx) + Postgres (StatefulSet) + Redis,
matching the shape this app already runs in locally via docker-compose.
Schema is Alembic-managed by a migration Job, not created by the app itself
on boot -- see `templates/migration-job.yaml` for why.

## Build and publish images to ACR

The Dockerfiles live in the `gridwork` repo, a separate repo sitting
alongside this one -- these commands run from *there*, not from here.

**AKS nodes are amd64.** If you're building on Apple Silicon (arm64), you
must cross-build with `--platform linux/amd64`, or the pods will crash-loop
with "exec format error" the moment Kubernetes actually tries to run them --
the image builds and pushes fine either way, so this mistake doesn't show up
until deploy time.

1. Log in to the ACR created in `../minimul_aks_001/main.tf`:

   ```bash
   az acr login --name aksdevacr123
   ```

2. From the `gridwork` repo root, build both images for `linux/amd64`:

   ```bash
   docker build --platform linux/amd64 -t aksdevacr123.azurecr.io/backend:latest ./assistant_backend
   docker build --platform linux/amd64 -t aksdevacr123.azurecr.io/frontend:latest ./assistant_web_next
   ```

   `assistant_web_next` -- the Next.js frontend -- not `assistant_web`,
   which is the old Create React App version, archived.

3. Push both:

   ```bash
   docker push aksdevacr123.azurecr.io/backend:latest
   docker push aksdevacr123.azurecr.io/frontend:latest
   ```

4. Confirm they actually landed:

   ```bash
   az acr repository list --name aksdevacr123 -o table
   ```

## Deploy to AKS

`values.yaml` already points at these images (`aksdevacr123.azurecr.io/...`,
`pullPolicy: Always`) -- the cluster can pull them because of the `AcrPull`
role assignment in `../minimul_aks_001/main.tf`.

```bash
helm upgrade --install gridwork ./gridwork \
  --set secrets.openaiApiKey="$OPENAI_API_KEY"
```

(Omit `--set secrets.openaiApiKey` to deploy without one -- chat's
`/completion` endpoint returns a clean `503` rather than crashing.)

Reach the frontend (it's a plain NodePort, no Ingress):

```bash
kubectl port-forward svc/gridwork-frontend 8080:80
```

## Re-deploying after a code change

Rebuild + push the relevant image (same commands as above), then:

```bash
helm upgrade gridwork ./gridwork
```

One gotcha with `pullPolicy: Always` + a mutable `latest` tag: Kubernetes
still won't roll pods over just because you pushed a new image under the
same tag -- nothing about the Deployment spec itself changed, so there's
nothing for Helm/Kubernetes to notice. Force it with:

```bash
kubectl rollout restart deployment/gridwork-backend deployment/gridwork-frontend
```

`helm upgrade` on its own is still needed first if anything in the chart
*did* change (env vars, replica counts, etc.) -- it also re-runs the
migration Job (`pre-upgrade` hook) before the new backend pods roll out.

## What's deliberately not here

Kept intentionally basic -- just backend, frontend, Postgres, Redis, and the
migration Job. No Ingress (the frontend Service is a plain NodePort), no
autoscaling (KEDA), no Azure Key Vault / Workload Identity integration, no
custom ServiceAccount, no HPA, PodDisruptionBudget, NetworkPolicy, or
resource requests/limits. `platform-lab/k8s/k8s_explorer/practice/full-stack-app/`
already has worked examples of each of these against a similar 3-tier shape
if/when this needs them -- kept out here to stay focused on "does the real
app actually work end-to-end in a cluster."

