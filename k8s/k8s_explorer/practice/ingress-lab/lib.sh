# Shared helpers for the ingress lab scripts. Sourced by run-problem.sh / run-solution.sh; not run directly.

# NS (the namespace) must be set by the calling script BEFORE sourcing this file.
: "${NS:?NS must be set by the calling script}"

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; CYAN=$'\033[36m'; RESET=$'\033[0m'

# --yes / -y : do not pause between steps (useful for re-running quickly)
INTERACTIVE=1
for arg in "$@"; do
  case "$arg" in -y|--yes) INTERACTIVE=0 ;; esac
done

step()    { echo; echo "${BOLD}${CYAN}=== STEP $1: $2${RESET}"; }
say()     { echo "${DIM}$*${RESET}"; }          # what is happening
look()    { echo "${YELLOW}LOOK FOR:${RESET} $*"; }
ok()      { echo "${GREEN}$*${RESET}"; }
bad()     { echo "${RED}$*${RESET}"; }
run()     { echo "${BOLD}\$ $*${RESET}"; "$@"; }   # print a command, then run it

pause() {
  [ "$INTERACTIVE" = 1 ] || return 0
  echo; read -r -p "${DIM}-- press Enter to continue (Ctrl+C to stop) --${RESET} " _
}

need_cluster() {
  kubectl get nodes >/dev/null 2>&1 || { bad "kubectl cannot reach a cluster. Is minikube running? Try: minikube status"; exit 1; }
}

# wait until the pod's log has at least N lines (up to 40s)
wait_log_lines() { # pod, n
  for _ in $(seq 1 20); do
    [ "$(kubectl -n $NS logs "$1" 2>/dev/null | grep -cE 'OK|FAILED')" -ge "$2" ] && return 0
    sleep 2
  done
  return 1
}

# run a one-off command in a throwaway pod inside the cluster, print its output
in_cluster() { # command...
  kubectl -n $NS run "tmp-$RANDOM" --image=busybox:1.36 --rm -i --restart=Never -- "$@" 2>&1 \
    | grep -v -E 'recorded in container logs|command prompt|^pod ".*" deleted' || true
}

# ---------- "outside the cluster" helpers (used by the NodePort lessons) ----------
# On macOS with the Docker driver, the minikube node is a container and your laptop cannot reach its IP.
# So we play "a client outside the cluster" with a throwaway Docker container on the same Docker network
# as the node: it can reach the node's IP (like another machine on the LAN) but it is NOT a Pod and
# knows nothing about Kubernetes (no cluster DNS, no Service names).

need_docker() {
  docker info >/dev/null 2>&1 || { bad "docker is not running. Start Docker Desktop and try again."; exit 1; }
}

# The profile name is normally the kubectl context name (and the node's Docker container name).
minikube_profile() {
  local c; c=$(kubectl config current-context 2>/dev/null || true)
  if [ -n "$c" ] && docker inspect "$c" >/dev/null 2>&1; then echo "$c"; else echo minikube; fi
}
node_ip() {
  local ip; ip=$(minikube ip -p "$(minikube_profile)" 2>/dev/null) || return 1
  [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
  echo "$ip"
}
node_net()         { docker inspect "$(minikube_profile)" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}'; }

# one request from outside; prints the first line of the reply or the error
outside_get() { # url
  docker run --rm --network "$(node_net)" busybox:1.36 sh -c "wget -T 3 -qO- $1 2>&1 | head -1"
}

# N requests from outside, then a count of what came back
outside_loop() { # url n
  docker run --rm --network "$(node_net)" busybox:1.36 sh -c \
    "for i in \$(seq $2); do wget -T 3 -qO- $1 2>/dev/null || echo 'FAILED (no reply)'; done" | sort | uniq -c
}

# wait until a URL answers from outside (kube-proxy needs a moment to program new rules), up to ~30s
wait_outside() { # url
  for _ in $(seq 1 15); do
    outside_get "$1" | grep -q '^Hello' && return 0
    sleep 2
  done
  return 1
}

# ---------- ingress helpers ----------
# The ingress controller (minikube addon) listens on port 80 of the node it runs on (hostPort).
# We reach it from a throwaway Docker container on the node's network, sending a Host header,
# exactly like a browser would when you type http://shop.local.

need_ingress() {
  kubectl get ingressclass nginx >/dev/null 2>&1 || {
    bad "No IngressClass 'nginx' found: the ingress controller is not installed."
    echo "Enable it with:  minikube addons enable ingress"; exit 1; }
  kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=120s >/dev/null 2>&1 || {
    bad "The ingress controller is not ready. Check: kubectl -n ingress-nginx get pods"; exit 1; }
}

# IP of the node the controller Pod runs on (it listens on that node's port 80)
controller_ip() {
  kubectl -n ingress-nginx get pod -l app.kubernetes.io/component=controller -o jsonpath='{.items[0].status.hostIP}'
}

# one request through the controller. Prints "<status line>  <body>" on one line.
ing_get() { # host path
  local ip; ip=$(controller_ip)
  docker run --rm --network "$(node_net)" busybox:1.36 sh -c \
    "wget -T 3 -S -qO- --header 'Host: $1' http://$ip$2 2>&1 | grep -E 'HTTP/|app, answered' | grep -v '^wget:' | tr '\n' ' ' | sed 's/  */ /g'; echo"
}

# wait until a host/path answers through the controller (the controller reloads its config after a new Ingress)
wait_ing() { # host path expected-text
  for _ in $(seq 1 20); do
    ing_get "$1" "$2" | grep -q "$3" && return 0
    sleep 2
  done
  return 1
}
