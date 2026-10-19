# Lab: Deploy a Model on Minikube

**Goal:** Run a PyTorch model API on Kubernetes using Minikube.
**Time:** ~90 minutes
**Requirements:** Docker, Minikube, and `kubectl` installed and working on your machine (install via your OS package manager or each project's official installation docs).

This lab walks through the full loop of containerizing a model-serving API and running it on a local single-node Kubernetes cluster: build an image, deploy it, expose it with a Service, scale it, read its logs, then tear it down.

## Before You Start: The Model API

This lab assumes you already have a small FastAPI application that serves a PyTorch model, made up of four files in one directory:

- **`app.py`** — a FastAPI app that loads `model.pt` at startup and exposes at least a `/predict` endpoint (FastAPI also gives you an interactive `/docs` page for free).
- **`model.pt`** — a PyTorch model saved with `torch.save()` (or exported as TorchScript).
- **`requirements.txt`** — lists `fastapi`, `uvicorn`, `torch`, and any other dependencies the app imports.
- **`Dockerfile`** — installs `requirements.txt` and runs the app with, e.g., `uvicorn app:app --host 0.0.0.0 --port 8000`. The server must listen on `0.0.0.0` (not `127.0.0.1`), otherwise it won't be reachable from outside its container.

If you don't already have this app, build a minimal version of these four files before continuing — the rest of the lab depends on having a working `/predict` endpoint listening on port 8000.

## 1. Start Minikube

```bash
minikube start --memory=4096 --cpus=4
```

This creates a local single-node Kubernetes cluster inside a VM/container, giving it 4096 MB of RAM and 4 CPUs to work with. Increase these values if your app or model is large — Minikube will fail to schedule pods if the node doesn't have enough allocatable memory/CPU.

Check that the cluster is up:

```bash
kubectl get nodes
```

✅ You should see one node with `STATUS = Ready`. If it shows `NotReady`, wait a few seconds and re-run the command — the node components can take a moment to initialize.

## 2. Build the Model API Container

Minikube runs its own internal Docker daemon, separate from your host machine's Docker. If you build the image with your host's Docker, Minikube's cluster won't be able to see it — you'd have to push it to a registry first. To skip that step for local development, point your shell's `docker` CLI at Minikube's daemon instead:

```bash
eval $(minikube docker-env)
docker build -t ai-model:latest .
docker images | grep ai-model
```

- `eval $(minikube docker-env)` — exports environment variables in your current shell so that subsequent `docker` commands talk to Minikube's Docker daemon instead of your host's.
- `docker build -t ai-model:latest .` — builds the image from the `Dockerfile` in the current directory, tagging it `ai-model:latest`.
- `docker images | grep ai-model` — confirms the image now exists inside Minikube's Docker, so the cluster can pull it locally without a registry.

✅ You should see `ai-model` with tag `latest` in the output.

**Note:** `eval $(minikube docker-env)` only affects your *current shell session*. If you open a new terminal, you'll need to re-run it before building or checking images again.

## 3. Create the Deployment

Save this as `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-model-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-model
  template:
    metadata:
      labels:
        app: ai-model
    spec:
      containers:
      - name: ai-model
        image: ai-model:latest
        ports:
        - containerPort: 8000
```

This tells Kubernetes to keep 2 identical replicas of the `ai-model:latest` image running at all times, each listening on container port 8000. If a pod crashes, the Deployment controller notices the replica count has dropped below 2 and starts a replacement — this is the self-healing behavior that makes Deployments preferable to running raw pods directly.

Apply it and watch the pods come up:

```bash
kubectl apply -f deployment.yaml
kubectl get pods
```

✅ Both pods should transition from `ContainerCreating` to `Running`. If a pod gets stuck or shows `ImagePullBackOff`, it usually means the image wasn't built inside Minikube's Docker daemon (revisit step 2) or `imagePullPolicy` is pulling from a registry instead of using the local image.

## 4. Expose It with a Service

A Deployment alone doesn't give you a stable way to reach the pods — pods get recreated with new internal IPs whenever they restart. A Service solves that by giving the set of pods a single stable address and load-balancing across them.

Save this as `service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-model-service
spec:
  selector:
    app: ai-model
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: NodePort
```

The `selector` (`app: ai-model`) is what connects this Service to the pods created by the Deployment — it matches on the pod label, not on the Deployment's name. `type: NodePort` is used here (rather than `LoadBalancer`) because a local Minikube cluster has no cloud provider to provision a real external load balancer; NodePort exposes the service on a port on the node itself instead.

Apply it:

```bash
kubectl apply -f service.yaml
kubectl get svc
```

✅ In the `PORT(S)` column you'll see something like `80:30080/TCP` — Kubernetes picked `30080` as the NodePort (the actual port number is assigned automatically from a default range and will vary).

## 5. Access the API

Rather than manually working out Minikube's VM IP and the assigned NodePort, let Minikube resolve the URL for you:

```bash
minikube service ai-model-service --url
```

This prints a URL such as `http://127.0.0.1:30080`. Open `<that URL>/docs` in a browser to reach FastAPI's auto-generated Swagger UI, and use it to try the `/predict` endpoint with a sample input (e.g., an image file, if that's what your model expects).

✅ A successful call to `/predict` returns your model's prediction as JSON.

## 6. Scale the Deployment

```bash
kubectl scale deployment ai-model-deployment --replicas=4
kubectl get pods
```

This changes the desired replica count from 2 to 4; the Deployment controller creates 2 more pods to match. The existing Service keeps working unchanged and automatically starts load-balancing across all 4 pods, since it selects pods by label rather than by a fixed list.

✅ `kubectl get pods` should now list 4 pods with `STATUS = Running`.

## 7. Inspect Logs

```bash
kubectl logs <pod-name>
```

Replace `<pod-name>` with one of the names from `kubectl get pods` (e.g., `ai-model-deployment-7d9f8c6b5-abcde`). This streams the container's stdout/stderr — for a FastAPI/Uvicorn app, that's the request access log plus any `print()`/logging output from your model code, which is the first place to look when a `/predict` call fails or misbehaves. Add `-f` to follow the log in real time, or `--previous` to see the log of a pod's last crashed instance.

## 8. Cleanup

```bash
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml
minikube stop
```

Deleting by file (`-f`) removes exactly the resources those manifests define. `minikube stop` shuts down the cluster VM/container (releasing the CPU/memory it was holding) without deleting it — a subsequent `minikube start` brings the same cluster back. Use `minikube delete` instead if you want to remove the cluster entirely.

✅ This frees your machine's resources after the lab.

## Learning Outcomes

By completing this lab, you will have:

- Deployed a containerized PyTorch model on Kubernetes.
- Exposed it via a Service for external access.
- Scaled replicas with `kubectl scale`.
- Gained first hands-on experience running an AI workload on Kubernetes.
