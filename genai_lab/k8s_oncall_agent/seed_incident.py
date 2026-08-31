#!/usr/bin/env python3
"""Deploy a real, reproducible broken scenario onto whatever cluster `kubectl config
current-context` points at - so the agent has an actual incident to investigate instead
of mocked JSON state (contrast with `../devops_sre_agent/seed_incident.py`, which mocks
an AWS fleet because real AWS costs money; a local minikube cluster is free and real).

The scenario: `checkout-api` is crash-looping. Its container always exits 1 immediately,
logging a realistic-looking dependency failure first - so `get_pod_logs` surfaces a
concrete, plausible root cause ("can't reach payments-db") for the agent to reason about
and report, even though the actual demo mechanism is just a bad container command, not a
real second service.

Run: python seed_incident.py
Undo: kubectl delete namespace <DEMO_NAMESPACE> (or `make clean`)
"""

from __future__ import annotations

from kubernetes import client, config as kube_config
from kubernetes.client.rest import ApiException

import config

CRASH_MESSAGE = (
    "FATAL: cannot connect to payments-db at payments-db.checkout.svc.cluster.local:5432 "
    "- connection refused"
)


def ensure_namespace(v1: client.CoreV1Api, name: str) -> None:
    try:
        v1.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=name)))
        print(f"created namespace/{name}")
    except ApiException as e:
        if e.status == 409:
            print(f"namespace/{name} already exists")
        else:
            raise


def apply_resource_quota(v1: client.CoreV1Api, namespace: str) -> None:
    quota = client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(name="checkout-quota"),
        spec=client.V1ResourceQuotaSpec(
            hard={"pods": "20", "requests.cpu": "4", "requests.memory": "4Gi"}
        ),
    )
    try:
        v1.create_namespaced_resource_quota(namespace, quota)
        print(f"created resourcequota/checkout-quota in {namespace} (generous - not the incident)")
    except ApiException as e:
        if e.status == 409:
            print("resourcequota/checkout-quota already exists")
        else:
            raise


def deploy_crashing_app(apps: client.AppsV1Api, namespace: str) -> None:
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="checkout-api"),
        spec=client.V1DeploymentSpec(
            replicas=2,
            selector=client.V1LabelSelector(match_labels={"app": "checkout-api"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "checkout-api"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="checkout-api",
                            image="busybox:1.36",
                            command=["sh", "-c", f"echo '{CRASH_MESSAGE}'; exit 1"],
                            # Required because checkout-quota sets requests.cpu/requests.memory:
                            # a ResourceQuota that constrains a resource type makes it mandatory
                            # on every container in the namespace - found this the hard way, the
                            # first seeded version had no requests here and every pod was
                            # rejected at admission with zero pods ever created at all.
                            resources=client.V1ResourceRequirements(
                                requests={"cpu": "50m", "memory": "32Mi"}
                            ),
                        )
                    ]
                ),
            ),
        ),
    )
    try:
        apps.create_namespaced_deployment(namespace, deployment)
        print(f"created deployment/checkout-api in {namespace} (2 replicas, will crash-loop)")
    except ApiException as e:
        if e.status == 409:
            print("deployment/checkout-api already exists")
        else:
            raise


def main() -> None:
    kube_config.load_kube_config()
    v1 = client.CoreV1Api()
    apps = client.AppsV1Api()

    ensure_namespace(v1, config.DEMO_NAMESPACE)
    apply_resource_quota(v1, config.DEMO_NAMESPACE)
    deploy_crashing_app(apps, config.DEMO_NAMESPACE)

    print(
        f"\nIncident seeded in namespace '{config.DEMO_NAMESPACE}'. Give it ~30s to start "
        f"crash-looping, then try:\n"
        f'  python agent.py "What\'s wrong in the {config.DEMO_NAMESPACE} namespace?"\n'
        f"Undo with: kubectl delete namespace {config.DEMO_NAMESPACE}  (or: make clean)"
    )


if __name__ == "__main__":
    main()
