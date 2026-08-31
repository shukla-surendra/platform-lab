# k8s/k8s_mlops

A small, real deployment exercise: run [Evidently](../../mlops_aiops/docs/tools/evidently/README.md)'s
self-hosted monitoring server as one Kubernetes pod, and a Jupyter notebook
as a second pod in the same cluster that computes a report and pushes it to
the server pod over the network — both deployed by a single Helm chart.

## Layout

```
k8s/k8s_mlops/
  docs/              -- Theory/reference docs (mkdocs docs_dir); empty for now,
                        add write-ups here as they're needed.
  practice/
    evidently_stack/ -- One Helm chart, two Deployments + two Services
                        (both NodePort) + a PVC for the server's workspace.
                        Also holds the two Dockerfiles (no official image
                        exists for either) and the notebook baked into the
                        jupyter-client image at build time.
```

## Why one chart, not two

Earlier this was two independent charts (`evidently_server/` and
`jupyter_client/`), each with its own `helm install`. Merged into one because
neither pod is useful without the other for this demo — they're always
installed and removed together — and splitting them bought nothing except
having to keep `jupyter-client`'s `EVIDENTLY_SERVER_URL` manually in sync
with whatever release name `evidently-server` happened to be installed
under. In one chart, that URL is computed directly from the shared release
name inside a template helper (`templates/_helpers.tpl`), so it's correct
automatically instead of being a value you set by hand.

## Architecture

```
┌────────────────────────────┐    HTTP (RemoteWorkspace.add_run)   ┌──────────────────────────┐
│  jupyter-client (pod)      │ ───────────────────────────────────▶│  evidently-server (pod)  │
│  - notebook baked into the │   POST snapshot                     │  - evidently ui           │
│    image, computes a       │                                     │    --host 0.0.0.0         │
│    Report locally           │                                     │    --workspace /workspace│
│  - Report.run() -> Snapshot│                                     │  - Service: NodePort 8000 │
│  - Service: NodePort 8888  │                                     │  - PVC: /workspace         │
└────────────────────────────┘                                     └──────────────────────────┘
              └────────────────── one `helm install`, one release ─────────────────┘
```

The report itself is computed **client-side**, inside the `jupyter-client`
pod; the server's only job is to store the resulting `Snapshot` and serve
the UI — this is exactly how Evidently's own `RemoteWorkspace` is designed
to work (verified from `evidently/ui/workspace.py`), not a workaround. The
two NodePorts exist only so *you* can reach each pod's UI from a host
browser — the pods themselves talk to each other over plain in-cluster
Service DNS, unrelated to either NodePort.

## Quickstart

See [`practice/evidently_stack/README.md`](practice/evidently_stack/README.md) for the full
detail. Short version:

```bash
cd practice/evidently_stack
minikube image build -t evidently-server:local -f Dockerfile.evidently-server .
minikube image build -t jupyter-client:local -f Dockerfile.jupyter-client .
helm install evidently . -n evidently --create-namespace
minikube service evidently-jupyter-client -n evidently --url
minikube service evidently-evidently-server -n evidently --url
```

## Related

- [`mlops_aiops/docs/tools/evidently/README.md`](../../mlops_aiops/docs/tools/evidently/README.md) —
  the full Evidently write-up (what it is, alternatives, and the
  `projects/evidently-monitoring-demo/` notebook which runs everything in
  one local process instead of split across two pods).
- [`k8s/k8s_explorer/`](../k8s/k8s_explorer/) — the general Kubernetes practice repo
  this chart follows the same conventions as (NodePort for local-cluster
  external access, `_helpers.tpl` naming, PVC persistence toggles).
