# evidently-stack (Helm chart)

One chart, two Deployments: a self-hosted [Evidently](../../../../mlops_aiops/docs/tools/evidently/README.md)
monitoring server (`evidently ui`), and a Jupyter pod whose notebook computes
a report and pushes it to that server over the network. One chart because
both pods are always installed/removed together for this demo and neither
is independently useful without the other — see [`../../README.md`](../../README.md)
for the full architecture.

## Build both images

No official image exists for either (checked Evidently's and Jupyter
docker-stacks' own docs/GitHub), so both are built from the Dockerfiles in
this directory.

**minikube** (loads straight into minikube's own Docker daemon — no
registry/push needed):

```bash
minikube image build -t evidently-server:local -f Dockerfile.evidently-server .
minikube image build -t jupyter-client:local -f Dockerfile.jupyter-client .
```

**kind**:

```bash
docker build -t evidently-server:local -f Dockerfile.evidently-server .
docker build -t jupyter-client:local -f Dockerfile.jupyter-client .
kind load docker-image evidently-server:local
kind load docker-image jupyter-client:local
```

## Install

```bash
helm install evidently . -n evidently --create-namespace
```

## Open both UIs

```bash
minikube service evidently-evidently-server -n evidently --url
minikube service evidently-jupyter-client -n evidently --url
```

Open the JupyterLab URL (token: `evidently-demo`, see `values.yaml`'s
`jupyterClient.jupyterToken`), run `work/evidently_client_demo.ipynb`, then
open the Evidently UI URL to see the uploaded report.

`jupyter-client`'s `EVIDENTLY_SERVER_URL` is computed inside the chart from
`evidently-server`'s own templated Service name (see
`templates/_helpers.tpl` and `templates/jupyter-client-deployment.yaml`) —
nothing to wire up manually, and it can't drift out of sync the way it could
across two independently-released charts.

## Uninstall

```bash
helm uninstall evidently -n evidently
```
