#!/usr/bin/env bash
# Solution 2: a NodePort Service opens a port on every node, so clients OUTSIDE the cluster can reach the backend.
# Fully independent: creates its own backend in its own namespace (solution2).
# Run:  ./run-solution.sh          (pauses between steps)
#       ./run-solution.sh --yes    (no pauses)
set -euo pipefail
cd "$(dirname "$0")"
NS=solution2
source ../lib.sh

need_cluster; need_docker
NODE_IP=$(node_ip) || { bad "Cannot find the minikube node IP (is this a minikube cluster, and is it running?)"; exit 1; }
NODE_PORT=30080       # the nodePort set in 02-service-nodeport.yaml

step 1 "Create the backend (3 Pods) and a plain ClusterIP Service (the 'before')"
say "This is the starting point of the problem: a Service that only works inside the cluster."
run kubectl apply -f 00-backend.yaml
run kubectl -n $NS rollout status deploy/backend --timeout=120s
run kubectl apply -f 01-service-clusterip.yaml
echo
run kubectl -n $NS get svc backend-svc
look "TYPE ClusterIP, EXTERNAL-IP <none>, PORT(S) 80/TCP (no node port)."
pause

step 2 "Confirm: from OUTSIDE the cluster, the backend is unreachable"
say "Outside client = a throwaway Docker container on the node's network (not a Pod). Node IP: $NODE_IP"
echo "${BOLD}http://$NODE_IP:$NODE_PORT${RESET}  ->  $(outside_get http://$NODE_IP:$NODE_PORT)"
look "'Connection refused' (nothing is listening on that port yet)."
pause

step 3 "THE FIX: change the Service type to NodePort"
say "Same Service, same name. Only 'type' changes, and we pin the port. Open 02-service-nodeport.yaml to read it:"
echo "${DIM}    type: NodePort"; echo "    ports: - port: 80  targetPort: 80  nodePort: $NODE_PORT${RESET}"
BEFORE_IP=$(kubectl -n $NS get svc backend-svc -o jsonpath='{.spec.clusterIP}')
run kubectl apply -f 02-service-nodeport.yaml
echo
run kubectl -n $NS get svc backend-svc
AFTER_IP=$(kubectl -n $NS get svc backend-svc -o jsonpath='{.spec.clusterIP}')
look "TYPE is now NodePort and PORT(S) shows 80:$NODE_PORT/TCP  ('service port : node port')."
look "CLUSTER-IP is still $AFTER_IP (before: $BEFORE_IP). A NodePort Service keeps its ClusterIP."
pause

step 4 "Call the backend from OUTSIDE the cluster"
say "Waiting for kube-proxy to program the new rule on the node (a few seconds)..."
wait_outside "http://$NODE_IP:$NODE_PORT" || bad "no reply yet; the next command will show what happens"
echo
echo "${BOLD}12 requests to http://$NODE_IP:$NODE_PORT from outside:${RESET}"
outside_loop "http://$NODE_IP:$NODE_PORT" 12
look "Replies from DIFFERENT Pods. The node port forwards to the Service, which spreads the load."
pause

step 5 "Callers INSIDE the cluster still work (nothing changed for them)"
say "The Service name and port are the same as before."
in_cluster sh -c 'for i in 1 2 3 4 5 6; do wget -qO- http://backend-svc; done' | sort | uniq -c
look "Still works. NodePort adds a way in; it does not remove the ClusterIP."
pause

step 6 "How it works: the rule on the node"
say "kube-proxy turned the NodePort into forwarding rules on the node. Looking at them inside the node:"
minikube ssh "sudo iptables -t nat -S KUBE-NODEPORTS | grep 'solution2/backend-svc'" 2>/dev/null | sed 's/^/  /' || true
say "Read it as: kube-proxy added rules to the chain KUBE-NODEPORTS for this Service. They hand incoming node-port traffic"
say "to the Service's own rules (KUBE-EXT-...), which then pick one of the Pods."
say "(This node's iptables does not print the port number inside the rule, so 30080 isn't visible here. Step 4 is the proof:"
say " the requests to port $NODE_PORT worked.) I checked with \`ss -ltn\` on this node: no process listens on $NODE_PORT. It is only a forwarding rule."
pause

step 7 "Kill a Pod: the outside caller keeps working"
VICTIM=$(kubectl -n $NS get pods -l app=backend -o jsonpath='{.items[0].metadata.name}')
say "Deleting $VICTIM while 20 requests are made from outside."
kubectl -n $NS delete pod "$VICTIM" --wait=false >/dev/null
outside_loop "http://$NODE_IP:$NODE_PORT" 20
look "20 replies in total and no 'FAILED'. (A single blip right at the instant a Pod terminates is possible.)"
pause

step 8 "Result, and what NodePort does NOT solve"
echo
ok "SOLVED: a client outside the cluster reaches the backend at http://<node-ip>:$NODE_PORT."
echo
say "Limits of NodePort (this is why the next lesson exists):"
say "  * clients must know a NODE's IP and a high port (30000-32767), not a nice name or port 80"
say "  * the node IP can change, and if that one node dies the client has no automatic failover to another node"
say "  * every Service needs its own port, and the port range is small"
say "  * you are exposing the nodes themselves"
echo
say "Try it from your Mac browser (Docker Desktop on macOS can't reach the node IP directly, so minikube makes a tunnel):"
say "    minikube service backend-svc -n $NS --url        # prints http://127.0.0.1:<port>; keep that terminal open"
echo
echo "Clean up with: ./cleanup.sh"
