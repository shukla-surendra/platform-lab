"""
Toy Kubernetes controller — the reconcile-loop pattern from scratch, no framework.

What real operators (KubeRay, Kubeflow's Argo-based pipelines, Kargo — all used elsewhere in
this repo as installed, third-party controllers) do internally, stripped down to the minimum
that still demonstrates the actual mechanism instead of just using someone else's:

    SharedInformer (watch + list)  ->  workqueue (dedupe + retry)  ->  reconcile (idempotent)
                                              ^
                                    resync ticker (self-heal on a timer, not just on events)

Behavior: any Namespace labeled `toy-controller/managed=true` gets a ResourceQuota and a
default-deny NetworkPolicy created inside it automatically, and kept there even if deleted by
hand — because reconcile() always re-derives desired state from the live cluster, it never
trusts the watch event payload.
"""

import logging
import queue
import threading
import time

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("toy-controller")

MANAGED_LABEL = "toy-controller/managed"
QUOTA_NAME = "toy-quota"
NETPOL_NAME = "toy-default-deny"
RESYNC_INTERVAL_SECONDS = 30
MAX_RETRIES = 5


def load_config():
    try:
        config.load_incluster_config()
        log.info("using in-cluster config (running as a Pod)")
    except config.ConfigException:
        config.load_kube_config()
        log.info("using local kubeconfig (running out-of-cluster)")


class Workqueue:
    """
    Minimal stand-in for client-go's workqueue.RateLimitingInterface: a FIFO queue with
    dedup on the *key* (namespace name), not the event. Multiple ADDED/MODIFIED events for
    the same namespace collapse into a single pending reconcile — this is what makes the
    pattern level-triggered instead of edge-triggered. Losing or coalescing individual events
    is fine, because reconcile() re-reads live state rather than acting on the event itself.
    """

    def __init__(self):
        self._q = queue.Queue()
        self._pending = set()
        self._lock = threading.Lock()

    def add(self, key: str):
        with self._lock:
            if key in self._pending:
                return  # already queued — dedup
            self._pending.add(key)
            self._q.put(key)

    def get(self) -> str:
        key = self._q.get()
        with self._lock:
            self._pending.discard(key)
        return key


def ensure_resource_quota(core_v1: client.CoreV1Api, namespace: str):
    body = client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(name=QUOTA_NAME),
        spec=client.V1ResourceQuotaSpec(
            hard={"pods": "10", "requests.cpu": "1", "requests.memory": "1Gi"}
        ),
    )
    try:
        core_v1.create_namespaced_resource_quota(namespace, body)
        log.info("ns=%s created ResourceQuota/%s", namespace, QUOTA_NAME)
    except ApiException as e:
        if e.status == 409:
            pass  # already exists — idempotent, nothing to do
        else:
            raise


def ensure_default_deny_netpol(net_v1: client.NetworkingV1Api, namespace: str):
    body = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(name=NETPOL_NAME),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(),  # empty selector = every Pod in the ns
            policy_types=["Ingress"],
        ),
    )
    try:
        net_v1.create_namespaced_network_policy(namespace, body)
        log.info("ns=%s created NetworkPolicy/%s (default-deny ingress)", namespace, NETPOL_NAME)
    except ApiException as e:
        if e.status == 409:
            pass
        else:
            raise


def reconcile(core_v1: client.CoreV1Api, net_v1: client.NetworkingV1Api, namespace: str):
    """
    The whole point: this function does NOT receive the watch event. It re-reads the
    namespace's current label from the API server and re-derives everything from that,
    every time it runs — on a real event, on resync, or on a retry after a transient error.
    """
    try:
        ns = core_v1.read_namespace(namespace)
    except ApiException as e:
        if e.status == 404:
            log.info("ns=%s no longer exists, nothing to reconcile", namespace)
            return
        raise

    labels = ns.metadata.labels or {}
    if labels.get(MANAGED_LABEL) != "true":
        log.info("ns=%s not managed (label %s != true), skipping", namespace, MANAGED_LABEL)
        return

    ensure_resource_quota(core_v1, namespace)
    ensure_default_deny_netpol(net_v1, namespace)
    log.info("ns=%s reconciled OK", namespace)


def watch_namespaces(wq: Workqueue):
    core_v1 = client.CoreV1Api()
    w = watch.Watch()
    log.info("watch loop started")
    while True:
        try:
            for event in w.stream(core_v1.list_namespace, timeout_seconds=0):
                ns_name = event["object"].metadata.name
                log.debug("watch event=%s ns=%s", event["type"], ns_name)
                wq.add(ns_name)
        except Exception:
            log.exception("watch stream broke, restarting in 2s")
            time.sleep(2)


def resync_loop(wq: Workqueue):
    """
    Proves the loop is level-triggered: even if a watch event is dropped (network blip,
    controller restart between watch resource versions, etc.), every managed namespace gets
    re-checked on a fixed cadence regardless of whether anything notified us.
    """
    core_v1 = client.CoreV1Api()
    while True:
        time.sleep(RESYNC_INTERVAL_SECONDS)
        try:
            for ns in core_v1.list_namespace().items:
                wq.add(ns.metadata.name)
            log.info("resync: re-enqueued %d namespaces", len(core_v1.list_namespace().items))
        except Exception:
            log.exception("resync list failed, will retry next tick")


def worker(wq: Workqueue):
    core_v1 = client.CoreV1Api()
    net_v1 = client.NetworkingV1Api()
    retries: dict[str, int] = {}
    while True:
        ns_name = wq.get()
        try:
            reconcile(core_v1, net_v1, ns_name)
            retries.pop(ns_name, None)
        except Exception:
            count = retries.get(ns_name, 0) + 1
            retries[ns_name] = count
            log.exception("reconcile ns=%s failed (attempt %d)", ns_name, count)
            if count <= MAX_RETRIES:
                backoff = min(2**count, 30)
                threading.Timer(backoff, wq.add, args=(ns_name,)).start()
            else:
                log.error("ns=%s exceeded MAX_RETRIES, giving up until next resync", ns_name)


def main():
    load_config()
    wq = Workqueue()
    threading.Thread(target=watch_namespaces, args=(wq,), daemon=True).start()
    threading.Thread(target=resync_loop, args=(wq,), daemon=True).start()
    worker(wq)  # runs forever on the main thread


if __name__ == "__main__":
    main()
