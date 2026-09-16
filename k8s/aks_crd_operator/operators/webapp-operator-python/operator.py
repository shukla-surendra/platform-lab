"""Python/kopf reimplementation of ../webapp-operator's
internal/controller/webapp_controller.go -- same CRD
(webapp.platformlab.dev/v1alpha1 WebApp), same reconcile behavior: ensure a
matching Deployment + Service, report availableReplicas back to status,
self-heal on drift. Written for side-by-side comparison with the Go
version, not to replace it -- see docs/qna.md for the tradeoffs.

Run locally against your current kubeconfig, no build/push needed:
    pip install -r requirements.txt
    kopf run operator.py --namespace default

Don't run this alongside the Go operator against the same WebApp objects --
two controllers reconciling the same CR fight each other. Scale the Go one
to zero first:
    kubectl scale deploy/webapp-operator-scaffold-controller-manager \
        -n webapp-operator-scaffold-system --replicas=0
"""

import kopf
import kubernetes
from kubernetes.client.exceptions import ApiException

GROUP = "webapp.platformlab.dev"
VERSION = "v1alpha1"
PLURAL = "webapps"


def labels_for(name: str) -> dict:
    return {
        "app.kubernetes.io/name": "webapp",
        "app.kubernetes.io/instance": name,
        "app.kubernetes.io/managed-by": "webapp-operator-python",
    }


def build_deployment(name, namespace, image, replicas, port, labels):
    return kubernetes.client.V1Deployment(
        metadata=kubernetes.client.V1ObjectMeta(
            name=name, namespace=namespace, labels=labels
        ),
        spec=kubernetes.client.V1DeploymentSpec(
            replicas=replicas,
            selector=kubernetes.client.V1LabelSelector(match_labels=labels),
            template=kubernetes.client.V1PodTemplateSpec(
                metadata=kubernetes.client.V1ObjectMeta(labels=labels),
                spec=kubernetes.client.V1PodSpec(
                    containers=[
                        kubernetes.client.V1Container(
                            name="webapp",
                            image=image,
                            ports=[
                                kubernetes.client.V1ContainerPort(
                                    container_port=port
                                )
                            ],
                        )
                    ]
                ),
            ),
        ),
    )


def build_service(name, namespace, port, labels):
    return kubernetes.client.V1Service(
        metadata=kubernetes.client.V1ObjectMeta(
            name=name, namespace=namespace, labels=labels
        ),
        spec=kubernetes.client.V1ServiceSpec(
            selector=labels,
            ports=[kubernetes.client.V1ServicePort(port=80, target_port=port)],
        ),
    )


def apply_deployment(apps_v1, deployment, name, namespace):
    try:
        apps_v1.create_namespaced_deployment(namespace, deployment)
    except ApiException as e:
        if e.status != 409:
            raise
        apps_v1.patch_namespaced_deployment(name, namespace, deployment)


def apply_service(core_v1, service, name, namespace):
    try:
        core_v1.create_namespaced_service(namespace, service)
    except ApiException as e:
        if e.status != 409:
            raise
        # clusterIP is immutable -- patch in place, don't replace wholesale.
        core_v1.patch_namespaced_service(name, namespace, service)


def ensure_children(spec, name, namespace, patch, logger):
    image = spec["image"]
    replicas = spec.get("replicas", 1)
    port = spec.get("port", 8080)
    labels = labels_for(name)

    apps_v1 = kubernetes.client.AppsV1Api()
    core_v1 = kubernetes.client.CoreV1Api()

    deployment = build_deployment(name, namespace, image, replicas, port, labels)
    kopf.adopt(deployment)  # sets ownerReferences -> WebApp, like
    apply_deployment(apps_v1, deployment, name, namespace)  # SetControllerReference in the Go version

    service = build_service(name, namespace, port, labels)
    kopf.adopt(service)
    apply_service(core_v1, service, name, namespace)

    try:
        dep_status = apps_v1.read_namespaced_deployment_status(name, namespace)
        available = dep_status.status.available_replicas or 0
    except ApiException:
        available = 0

    if patch is not None:
        patch.status["availableReplicas"] = available

    logger.info(f"reconciled WebApp {namespace}/{name}")


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
@kopf.on.resume(GROUP, VERSION, PLURAL)
def reconcile(spec, name, namespace, patch, logger, **_):
    ensure_children(spec, name, namespace, patch, logger)


# controller-runtime's Owns() re-triggers Reconcile the instant an owned
# Deployment/Service is edited or deleted (event-driven, near-instant).
# kopf's simplest equivalent is a periodic timer that re-asserts desired
# state -- self-healing on a delay instead of instantly. See docs/qna.md
# for the tradeoff and how to get event-driven self-heal in kopf instead.
@kopf.timer(GROUP, VERSION, PLURAL, interval=30)
def resync(spec, name, namespace, patch, logger, **_):
    ensure_children(spec, name, namespace, patch, logger)


# No finalizer needed -- deleting a WebApp lets Kubernetes garbage-collect
# the owned Deployment/Service via the ownerReference kopf.adopt() set,
# same reasoning as the Go version (see docs/02-crd-design.md).
