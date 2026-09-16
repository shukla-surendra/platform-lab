"""kopf operator for the Greeting CRD (greeting.platformlab.dev/v1alpha1).

Reconciles a `Greeting` into an owned `ConfigMap` containing the rendered
message. Deliberately the smallest possible shape -- see ../README.md for
the problem statement and CRD design, and ../webapp-operator-python for the
same pattern applied to a Deployment+Service instead of a single ConfigMap.

Run locally against your current kubeconfig, no build/push needed:
    pip install -r requirements.txt
    kopf run operator.py --namespace default
"""

import kopf
import kubernetes
from kubernetes.client.exceptions import ApiException

GROUP = "greeting.platformlab.dev"
VERSION = "v1alpha1"
PLURAL = "greetings"

DEFAULT_MESSAGE = "Hello, {name}!"


def render(message: str, name: str) -> str:
    return message.replace("{name}", name)


def configmap_name(greeting_name: str) -> str:
    return f"{greeting_name}-greeting"


def build_configmap(greeting_name, namespace, rendered):
    return kubernetes.client.V1ConfigMap(
        metadata=kubernetes.client.V1ObjectMeta(
            name=configmap_name(greeting_name),
            namespace=namespace,
            labels={
                "app.kubernetes.io/name": "greeting",
                "app.kubernetes.io/instance": greeting_name,
                "app.kubernetes.io/managed-by": "greeting-operator",
            },
        ),
        data={"greeting": rendered},
    )


def apply_configmap(core_v1, configmap, name, namespace):
    try:
        core_v1.create_namespaced_config_map(namespace, configmap)
    except ApiException as e:
        if e.status != 409:
            raise
        core_v1.patch_namespaced_config_map(name, namespace, configmap)


def ensure_child(spec, name, namespace, meta, patch, logger):
    who = spec["name"]
    message = spec.get("message", DEFAULT_MESSAGE)
    rendered = render(message, who)

    core_v1 = kubernetes.client.CoreV1Api()

    cm = build_configmap(name, namespace, rendered)
    kopf.adopt(cm)  # ownerReferences -> this Greeting; enables GC on delete
    apply_configmap(core_v1, cm, configmap_name(name), namespace)

    if patch is not None:
        patch.status["configMapName"] = configmap_name(name)
        patch.status["observedGeneration"] = meta["generation"]

    logger.info(f"reconciled Greeting {namespace}/{name} -> {configmap_name(name)}")


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
@kopf.on.resume(GROUP, VERSION, PLURAL)
def reconcile(spec, name, namespace, meta, patch, logger, **_):
    ensure_child(spec, name, namespace, meta, patch, logger)


# Same tradeoff as webapp-operator-python: a periodic timer instead of an
# event-driven watch on the owned ConfigMap. Drift (someone edits/deletes
# the ConfigMap directly) gets corrected on the next tick, not instantly.
@kopf.timer(GROUP, VERSION, PLURAL, interval=30)
def resync(spec, name, namespace, meta, patch, logger, **_):
    ensure_child(spec, name, namespace, meta, patch, logger)


# No finalizer *written here* -- deleting a Greeting lets Kubernetes
# garbage-collect the owned ConfigMap via the ownerReference kopf.adopt()
# set, same reasoning as the Go version. kopf itself still adds its own
# `kopf.zalando.org/KopfFinalizerMarker` to every resource it manages,
# regardless of whether a delete handler is defined -- confirmed via
# `kubectl get greeting alice -o jsonpath='{.metadata.finalizers}'` after a
# live test run. See ../README.md and docs/qna.md for the implication:
# a Greeting only actually deletes once the operator pod is up to remove
# that finalizer, unlike the Go version where deletion never depends on
# the controller being alive.
