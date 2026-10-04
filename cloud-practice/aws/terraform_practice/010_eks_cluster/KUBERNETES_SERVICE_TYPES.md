# Kubernetes Service types, and what ClusterIP does

Values like `172.20.100.11` and port `30238` come from the lab run (cluster since destroyed).

## 1. The four Service types

| Type | What it does | Reachable from | Used in this lab? |
|---|---|---|---|
| **ClusterIP** (default) | Virtual IP + DNS name inside the cluster | Inside the cluster only | **Yes**: `hello` |
| **NodePort** | Opens the same port (30000-32767) on every node, on top of a ClusterIP | Anything that can reach node IPs on that port | Indirectly: the LoadBalancer allocated one (30238) |
| **LoadBalancer** | Asks the cloud for an external load balancer, on top of NodePort + ClusterIP | The internet | **Yes**: `hello-lb` |
| **ExternalName** | DNS alias (CNAME) to an outside hostname; no proxying | Inside the cluster | No |

They build on each other:

```
LoadBalancer  =  NodePort  +  external cloud LB
NodePort      =  ClusterIP +  a port on every node
ClusterIP     =  the base
```

Variant: **headless Service** (`clusterIP: None`): no virtual IP; DNS returns pod IPs directly (StatefulSets, databases).

## 2. Not Service types

- **`kubectl port-forward`**: a debugging command that tunnels a local port to a pod/Service through the API server. Not a Service type, not for real users.
- **`kubectl proxy`**: local proxy to the API server (debugging).
- **Ingress / Gateway API**: HTTP routing (host/path) to Services; on AWS this is how you get an ALB (needs the AWS Load Balancer Controller).

## 3. What ClusterIP does

**Problem**: pods are temporary. Their IPs change on restart, reschedule and scale, so clients can't rely on them.

**Solution**: a Service gives a group of pods one stable address.

- A **virtual IP** that stays the same for the life of the Service (lab: `172.20.100.11`).
- A **DNS name**: `<service>.<namespace>.svc.cluster.local` (short: `hello.demo`, or `hello` within the same namespace), resolved by CoreDNS.
- The Service tracks pods matching its `selector` (`app=hello`) that are **Ready**; that list is the **Endpoints**.
- **kube-proxy** on every node programs rules (iptables or IPVS) so traffic to the virtual IP is forwarded to one of the Endpoints. Rules update as pods come and go.
- Balancing is per **connection**, not per request. Pods failing their readiness probe are removed from rotation.

```
client pod -> hello.demo (172.20.100.11:80)
           -> kube-proxy rules on the node
           -> one ready pod IP (10.20.x.x:80)
```

## 4. Properties worth remembering

- **Not a real address**: the ClusterIP isn't on any machine or interface; nothing answers it, so **you can't ping it**.
- **Only inside the cluster**: not reachable from your laptop or the internet. It comes from the Service CIDR (`172.20.0.0/16` here), separate from the VPC range (`10.20.x.x`).
- **Selector decides membership**: two Services can select the same pods (the lab's `hello` and `hello-lb` did).
- **Stable vs. temporary**: Service IP stable; pod IPs not.
- **Port mapping**: `port` is what clients use on the Service; `targetPort` is the container port.

## 5. Using and inspecting it

```
# from another pod in the cluster
curl http://hello.demo           # or http://hello in the same namespace

# from your laptop (debugging): tunnel through the API server
kubectl -n demo port-forward svc/hello 8080:80

# inspect
kubectl -n demo get svc hello           # shows CLUSTER-IP, PORT(S)
kubectl -n demo get endpoints hello     # the pod IPs it forwards to
kubectl -n demo describe svc hello
```

Typical uses: frontend -> backend, app -> database, any in-cluster service discovery.

## 6. Why the other types need it

NodePort and LoadBalancer each create a ClusterIP first and add an external entry on top. In the lab, the AWS Classic LB sent traffic to port 30238 on the nodes (NodePort), and kube-proxy forwarded it to a pod through the same ClusterIP-style rules.

Related: `ACCESSING_THE_APP.md`, `LOADBALANCER_SERVICE_BEHAVIOR.md`.
