#!/usr/bin/env bash
# Solution 1: one Ingress routes by host name and path to the right Service. One entrance for every app.
# Fully independent: creates its own apps in its own namespace (ingress-s1).
# Needs the ingress controller:  minikube addons enable ingress
# Run:  ./run-solution.sh          (pauses between steps)
#       ./run-solution.sh --yes    (no pauses)
set -euo pipefail
cd "$(dirname "$0")"
NS=ingress-s1
source ../lib.sh

need_cluster; need_docker; need_ingress
CIP=$(controller_ip)

step 1 "Create the three apps with plain ClusterIP Services (no external exposure)"
say "Same apps as the problem. This time their Services are ClusterIP: nothing about them is reachable from outside."
run kubectl apply -f 00-apps.yaml
for d in shop blog api; do kubectl -n $NS rollout status deploy/$d --timeout=120s >/dev/null; done
echo
run kubectl -n $NS get svc
look "TYPE ClusterIP and no node ports. The only way in will be the Ingress."
pause

step 2 "Before the Ingress: the controller is there, but knows no rules"
say "The ingress controller runs on node $CIP and listens on port 80. With no Ingress rules it answers 404 to everything."
echo "  shop.local -> $(ing_get shop.local /)"
look "404: the controller is reachable, but has nothing to route to yet."
pause

step 3 "THE FIX: create one Ingress"
say "An Ingress is just routing rules. Open 01-ingress.yaml to read them. The important lines:"
echo "${DIM}    ingressClassName: nginx                 # which controller implements this"
echo "    host: shop.local   path: /api   -> api-svc"
echo "    host: shop.local   path: /      -> shop-svc"
echo "    host: blog.local   path: /      -> blog-svc${RESET}"
run kubectl apply -f 01-ingress.yaml
echo
run kubectl -n $NS get ingress site
look "CLASS nginx and HOSTS shop.local,blog.local. ADDRESS fills in after a few seconds (the controller's address)."
pause

step 4 "Call the apps through the ONE entrance, choosing by host name and path"
say "Every request goes to the same address ($CIP:80). Only the Host header and the path change."
say "(A browser sends the Host header for you when you type http://shop.local. We send it by hand.)"
wait_ing shop.local / "shop app" || bad "no reply yet; the lines below show what happens"
echo
show() { printf "  %-26s -> %s\n" "$1$2" "$(ing_get "$1" "$2")"; }
show shop.local /
show shop.local /api
show blog.local /
echo
say "Things that match no rule:"
show unknown.local /
look "Each host/path reaches the right app. An unknown host gets the controller's 404: it has no rule for it."
pause

step 5 "How it works: the controller turned the Ingress into nginx config"
say "The controller is an nginx. It watches Ingress objects and regenerates its own config. The part it wrote for shop.local:"
kubectl -n ingress-nginx exec deploy/ingress-nginx-controller -- sh -c \
  "nginx -T 2>/dev/null | awk '/## start server shop.local/{f=1} f; /## end server shop.local/{exit}' | grep -E 'server_name|location |proxy_upstream_name' | grep -v '\"-\"\|internal'" \
  | sed 's/^[ \t]*/    /' | sed 's/set \$proxy_upstream_name/  sends to backend:/' || true
echo
say "Which Pods does it send to? The controller keeps its own list of backends. It uses the POD IPs, not the Service's ClusterIP:"
kubectl -n ingress-nginx exec deploy/ingress-nginx-controller -- sh -c "wget -qO- http://127.0.0.1:10246/configuration/backends 2>/dev/null" \
  | python3 -c '
import json, sys
for b in json.load(sys.stdin):
    if b["name"].startswith("ingress-s1-"):
        print("   ", b["name"], "->", ", ".join(e["address"] + ":" + e["port"] for e in b["endpoints"]))' || true
echo "  Actual Pod IPs:"
kubectl -n $NS get pods -l 'app in (shop,api,blog)' --field-selector=status.phase=Running -o custom-columns='    APP:.metadata.labels.app,IP:.status.podIP' --no-headers
echo "  Service ClusterIPs (NOT used by the controller):"
kubectl -n $NS get svc shop-svc blog-svc api-svc -o custom-columns='    NAME:.metadata.name,CLUSTERIP:.spec.clusterIP' --no-headers
look "An Ingress is NOT a proxy itself. It is a set of rules; the controller (nginx) does the proxying, straight to the Pods."
pause

step 6 "Kill a Pod: the entrance keeps working"
VICTIM=$(kubectl -n $NS get pods -l app=shop -o jsonpath='{.items[0].metadata.name}')
say "Deleting $VICTIM while 15 requests are made to shop.local."
kubectl -n $NS delete pod "$VICTIM" --wait=false >/dev/null
docker run --rm --network "$(node_net)" busybox:1.36 sh -c \
  "for i in \$(seq 15); do wget -T 3 -qO- --header 'Host: shop.local' http://$CIP/ 2>/dev/null || echo 'FAILED (no reply)'; done" \
  | sed 's/answered by pod //' | sort | uniq -c | sed 's/^/  /'
look "15 replies, no FAILED. The Ingress sends to Pods through the Service's live list, same as always."
pause

step 7 "Add a 4th app: change only the Ingress"
say "docs gets a ClusterIP Service (02-new-app.yaml) and ONE new rule: docs.local -> docs-svc (03-ingress-with-docs.yaml)."
say "No new port, no new load balancer, no change to the other apps."
run kubectl apply -f 02-new-app.yaml
kubectl -n $NS rollout status deploy/docs --timeout=120s >/dev/null
run kubectl apply -f 03-ingress-with-docs.yaml
wait_ing docs.local / "docs app" || bad "no reply yet; the lines below show what happens"
echo
show docs.local /
show shop.local /
look "docs.local works through the same entrance, and the others are unchanged."
pause

step 8 "Result, and what an Ingress does NOT do"
echo
ok "SOLVED: one entrance, many apps, routed by host name and path."
echo
say "What it does not do:"
say "  * It needs an ingress CONTROLLER installed. An Ingress object alone does nothing."
say "  * It is for HTTP/HTTPS. Plain TCP/UDP (a database port, say) needs a LoadBalancer or a controller-specific feature."
say "  * The controller itself still needs to be reachable from outside: on a cloud, that is ONE LoadBalancer in front of it."
say "  * Names like shop.local must resolve to the entrance. Locally you fake that with a Host header or /etc/hosts."
echo
say "Reach it from your Mac (Docker Desktop can't reach the node IP). Two options, see ../docs/02-enable-on-minikube.md:"
say "    kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8080:80      # then: curl -H 'Host: shop.local' http://127.0.0.1:8080/"
say "    minikube tunnel                                                               # then: curl -H 'Host: shop.local' http://127.0.0.1/"
echo
echo "Clean up with: ./cleanup.sh"
