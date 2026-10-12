#!/usr/bin/env bash
# Problem 2: a ClusterIP Service only works INSIDE the cluster. Something outside can't reach the backend.
# Run:  ./run-problem.sh          (pauses between steps)
#       ./run-problem.sh --yes    (no pauses)
set -euo pipefail
cd "$(dirname "$0")"
NS=problem2
source ../lib.sh

need_cluster; need_docker

step 1 "Create the backend and a ClusterIP Service"
say "3 backend Pods and the ClusterIP Service from lesson 1 (backend-svc)."
run kubectl apply -f 00-backend.yaml
run kubectl -n $NS rollout status deploy/backend --timeout=120s
echo
run kubectl -n $NS get pods -o wide
echo
run kubectl -n $NS get svc backend-svc
look "TYPE ClusterIP, a CLUSTER-IP, and EXTERNAL-IP <none>: there is no way in from outside."
pause

step 2 "Callers INSIDE the cluster work"
say "A throwaway Pod calls the Service by name, 6 times."
in_cluster sh -c 'for i in 1 2 3 4 5 6; do wget -qO- http://backend-svc; done' | sort | uniq -c
look "Replies from different Pods. Inside the cluster, the Service does its job."
pause

step 3 "Callers OUTSIDE the cluster do not"
NODE_IP=$(node_ip) || { bad "Cannot find the minikube node IP (is this a minikube cluster, and is it running?)"; exit 1; }
CLUSTER_IP=$(kubectl -n $NS get svc backend-svc -o jsonpath='{.spec.clusterIP}')
POD_IP=$(kubectl -n $NS get pods -l app=backend -o jsonpath='{.items[0].status.podIP}')
say "We need a client outside the cluster, like a browser, a mobile app or another team's server."
say "On your Mac the minikube node is not directly reachable, so we use a throwaway Docker container on the"
say "node's network: it reaches the node IP like another machine on the LAN, but it is NOT a Pod."
echo "node IP: $NODE_IP    Service ClusterIP: $CLUSTER_IP    one Pod IP: $POD_IP"
echo
echo "${BOLD}1) the Service's ClusterIP:${RESET}   http://$CLUSTER_IP"; echo "   -> $(outside_get http://$CLUSTER_IP)"
echo "${BOLD}2) a Pod's IP:${RESET}                http://$POD_IP";     echo "   -> $(outside_get http://$POD_IP)"
echo "${BOLD}3) the node's IP, port 80:${RESET}    http://$NODE_IP";    echo "   -> $(outside_get http://$NODE_IP)"
echo "${BOLD}4) the Service NAME:${RESET}          http://backend-svc"; echo "   -> $(outside_get http://backend-svc)"
look "All four fail: timed out, refused, or 'bad address'. Why each one fails:"
say "1) ClusterIP: a virtual IP that exists only as forwarding rules INSIDE the cluster's nodes. Not routable from outside."
say "2) Pod IP:    on the cluster's private Pod network. Not routable from outside (and it changes anyway)."
say "3) node IP:   the node is reachable, but nothing listens on port 80 on the node itself."
say "4) the name:  names like backend-svc are cluster DNS. A client outside the cluster can't resolve them."
pause

step 4 "The problem"
echo
bad "THE PROBLEM: the backend is healthy and the Service works, but nothing OUTSIDE the cluster can reach it."
say "A ClusterIP is for traffic that starts inside the cluster. We need a way in: a port on the node itself."
echo
echo "Next (independent of this folder, you can run it any time): cd ../solution2-nodeport && ./run-solution.sh"
echo "Clean up this lab with: ./cleanup.sh"
