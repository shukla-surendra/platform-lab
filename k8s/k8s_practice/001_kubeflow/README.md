# Basic Kubeflow Pipeline

Kubeflow Pipelines (KFP) runs a multi-step workflow on Kubernetes.
Each step is a Python function that runs in its own Pod.

## Concepts
- **Component**: one step (`@dsl.component`).
- **Pipeline**: how the steps connect (`@dsl.pipeline`).
- **Compile**: turns the Python into `pipeline.yaml`, which the cluster runs.

## Run it

```bash
pip install kfp
python pipeline.py            # creates pipeline.yaml
```

Then either:

1. **UI:** open the Kubeflow Pipelines UI, Pipelines > Upload pipeline > choose `pipeline.yaml` > Create run.
2. **Code:**
   ```python
   import kfp
   client = kfp.Client(host="http://localhost:8080")
   client.create_run_from_pipeline_package("pipeline.yaml", arguments={"a": 5, "b": 7})
   ```

## No cluster yet? Standalone KFP on kind/minikube

```bash
export PIPELINE_VERSION=2.3.0   # check the latest release on the kubeflow/pipelines GitHub
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic?ref=$PIPELINE_VERSION"

kubectl get pods -n kubeflow                              # wait until all Running
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80   # UI at http://localhost:8080
```

Clean up: `kubectl delete namespace kubeflow` (cluster-scoped resources from step 1 remain).

## Expected result
Run graph shows `add` then `show`. The `show` logs print `The result is 3`.
