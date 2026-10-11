#!/usr/bin/env bash
# Problem 1: three apps exposed with one NodePort each. It works, but it does not scale or look like a real site.
# Run:  ./run-problem.sh          (pauses between steps)
#       ./run-problem.sh --yes    (no pauses)
set -euo pipefail
cd "$(dirname "$0")"
NS=ingress-p1
source ../lib.sh

need_cluster; need_docker
NODE_IP=$(node_ip) || { bad "Cannot find the minikube node IP"; exit 1; }

step 1 "Three apps, each exposed with its own NodePort Service"
say "shop, blog and api. Each needs to be reachable from outside, so each gets a Service of type NodePort."
run kubectl apply -f 00-apps.yaml
for d in shop blog api; do kubectl -n $NS rollout status deploy/$d --timeout=120s >/dev/null; done
echo
run kubectl -n $NS get svc
look "Three Services, three different node ports: 30101, 30102, 30103."
pause

step 2 "It works, if the client knows the node IP and the right port for each app"
for pair in shop:30101 blog:30102 api:30103; do
  app=${pair%%:*}; port=${pair##*:}
  echo -n "  $app  -> http://$NODE_IP:$port   : "; outside_get "http://$NODE_IP:$port"
done
look "Each app answers, but only on its own port. A real user would have to type http://$NODE_IP:30102 for the blog."
pause

step 3 "The pain points"
say "1) A fourth app needs a fourth port. Ports are a shared, limited range (30000-32767). Try to reuse one:"
kubectl apply -f - <<'YAML' 2>&1 | sed 's/^/   /' || true
apiVersion: v1
kind: Service
metadata: {name: docs-svc, namespace: ingress-p1}
spec:
  type: NodePort
  selector: {app: docs}
  ports: [{port: 80, targetPort: 80, nodePort: 30101}]
YAML
look "An error: the node port is already allocated. Every app needs its own number."
echo
say "2) No names. Users want shop.example.com and blog.example.com, not an IP and a port."
say "3) No path routing. You cannot say 'everything under /api goes to the api app' on the same address."
say "4) Clients must know a NODE's IP, and nodes come and go. Every app is exposed on every node."
say "5) HTTPS (TLS), authentication, rate limiting, redirects: each would have to be solved inside every app,"
say "   because nothing sits in front of them."
pause

step 4 "The problem"
echo
bad "THE PROBLEM: this works for a demo, but it is port sprawl. We want ONE entry point that routes by host name and path."
say "That is exactly what an Ingress does: one external entrance, rules that send each host/path to the right Service."
echo
echo "Next (independent of this folder, you can run it any time): cd ../solution1-ingress && ./run-solution.sh"
echo "Clean up this lab with: ./cleanup.sh"
