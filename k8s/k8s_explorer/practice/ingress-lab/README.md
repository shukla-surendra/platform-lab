# Ingress Lab

Learn Kubernetes **Ingress**: what problem it solves, how to run it locally on minikube, and how the same idea works
on AWS (EKS). Same style as the Services lessons: a **problem** you see happen, then the **solution**, each
**independent**, each with a script.

> **Read this:** the controller used here, `ingress-nginx` (what minikube's `ingress` addon installs), was announced
> as **retired by the Kubernetes project** (best-effort maintenance until March 2026, then no more releases or
> security fixes). The **Ingress API** you learn here is the same with any controller, so the concepts carry over.
> Details and sources: [docs/01-concepts.md](docs/01-concepts.md).

## The idea in one picture

```
before (lesson: Service types)           after (this lab)
NodePort per app: 30101, 30102, ...      one entrance, routed by host name and path

 client ─> node:30101 ─> shop            client ─> shop.local      ┐
 client ─> node:30102 ─> blog                      blog.local      ├─> Ingress controller ─> shop / blog / api
 client ─> node:30103 ─> api                       shop.local/api  ┘      (rules from ONE Ingress)
```

## Learning path

| # | Folder | What you do |
|---|---|---|
| 1 | [`problem1-port-sprawl`](problem1-port-sprawl) | Three apps, three NodePorts: see why it doesn't scale |
| 2 | [`solution1-ingress`](solution1-ingress) | One Ingress: host- and path-based routing, add a 4th app with one rule |

Then read the docs:

| Doc | Covers |
|---|---|
| [01 Concepts](docs/01-concepts.md) | Ingress vs controller, rules, pathType, IngressClass, TLS, annotations, Gateway API, the ingress-nginx retirement |
| [02 Enable on minikube](docs/02-enable-on-minikube.md) | What you need, how to enable it, what the addon installs, how to reach it from macOS, checks |
| [03 AWS / EKS](docs/03-aws-eks.md) | AWS Load Balancer Controller (ALB) vs ingress-nginx + NLB, target types, IAM, subnet tags, example, pitfalls. **Not run on AWS** |
| [04 Troubleshooting](docs/04-troubleshooting.md) | Checklist and symptom table |

## Quick start

```bash
minikube addons enable ingress                    # installs the controller (once)
cd k8s/k8s_explorer/practice/ingress-lab/problem1-port-sprawl && ./run-problem.sh
cd ../solution1-ingress && ./run-solution.sh      # needs the addon
./cleanup.sh                                      # removes this lab (not the controller)
```

Each script pauses between steps (press Enter). Add `--yes` to skip the pauses. Docker must be running (it plays
"a client outside the cluster", the same trick as in the Services lessons).

## Using it by hand

After `kubectl apply -f .` in `solution1-ingress`, open a port-forward to the controller and call each app with a `Host:` header.
The commands, expected output, browser steps, things to try and troubleshooting are in
[`solution1-ingress/README.md`](solution1-ingress/README.md#using-it-by-hand-without-the-script).

```bash
kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8080:80        # terminal 1, keep open
curl -H "Host: shop.local" http://127.0.0.1:8080/                                 # terminal 2
```

## Folder layout

```
ingress-lab/
├── README.md
├── lib.sh                      shared helpers for the scripts
├── docs/                       concepts, minikube, AWS, troubleshooting
├── problem1-port-sprawl/       00-apps.yaml (3 NodePort apps), run-problem.sh, cleanup.sh, README.md
└── solution1-ingress/          00-apps.yaml, 01-ingress.yaml, 02-new-app.yaml, 03-ingress-with-docs.yaml,
                                run-solution.sh, cleanup.sh, README.md
```

## What was and was not verified

- **Run and checked on this machine:** both labs end to end on minikube (Docker driver, macOS, 2 nodes, Kubernetes
  v1.34.0, ingress-nginx controller v1.13.2); access through `kubectl port-forward` with Host headers; the controller's generated
  nginx config and its Pod-IP backend list.
- **Not tested:** `minikube tunnel`, browser access via `/etc/hosts`, TLS, and **everything on AWS**.
