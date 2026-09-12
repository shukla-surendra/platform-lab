# Debugging: Getting a Shell on a Node (No SSH)

See [`README.md`](README.md#getting-a-shell-on-a-node-vm-no-ssh) for why
this is the deliberate, production-pattern way in — no SSH key, no open
port 22, no Azure Bastion.

## `kubectl debug node`

Current node names in this cluster (now two pools, one node each — see
the README's "Two node pools" section):

```bash
kubectl get nodes -o wide -L kubernetes.azure.com/agentpool
```

```
node/aks-system-19418211-vmss000000   (agentpool: system)
node/aks-user-30842888-vmss000000     (agentpool: user)
```

Get a root shell on either one:

```bash
# system pool node
kubectl debug node/aks-system-19418211-vmss000000 -it \
  --image=mcr.microsoft.com/dotnet/runtime-deps:8.0 -- chroot /host bash

# user pool node
kubectl debug node/aks-user-30842888-vmss000000 -it \
  --image=mcr.microsoft.com/dotnet/runtime-deps:8.0 -- chroot /host bash
```

(Node names change if a pool is ever rotated — e.g. the system pool's
name changed from `aks-system-12333642-...` to `aks-system-19418211-...`
the moment `only_critical_addons_enabled` was applied, since that
specific change forces Azure to actually replace the node, not just
relabel it. Always re-run `kubectl get nodes` rather than assuming a
name from an earlier session still exists.)

Once inside, you're root on the actual VM — `hostname`, `uname -a`,
`df -h`, `ps aux`, `cat /etc/os-release`, `journalctl -xe`, whatever you
want.

## What to actually do once you're in there

Grouped by what each thing teaches you, not just a command list.

**Container runtime — the real containers, not the k8s abstraction**
```bash
crictl ps          # every container via containerd's CRI directly -- bypasses the k8s API entirely
crictl images      # what's actually pulled onto this node
crictl logs <id>   # same content kubectl logs reads, straight from the source
```
Verified live: `crictl ps` lists things `kubectl get pods` never shows you
this directly — the debug pod itself, `coredns`, `azure-cns`,
`csi-azuredisk-node` sidecars, each as a real containerd container with
its own ID. This is the ground truth; `kubectl` is a layer on top of it.
For what every one of those containers/pods actually is and why it's
there, see **[`node-anatomy.md`](node-anatomy.md)** — a full survey of
everything present on a bare node, with nothing deployed.

**Kubelet — the agent that makes this node part of the cluster at all**
```bash
systemctl status kubelet        # confirmed "active" on this cluster
journalctl -u kubelet -n 200    # the single most useful log when a node acts up
cat /var/lib/kubelet/config.yaml
ls /etc/kubernetes/             # certs, manifests
```

**Networking — how Services/CNI actually work at the packet level**
```bash
cat /etc/cni/net.d/*.conflist        # confirmed live: Azure CNI, transparent mode, azure-cns IPAM
ip addr
iptables -t nat -L KUBE-SERVICES     # how a ClusterIP routes to real pod IPs
```
Real gotcha hit live: `iptables` failed with `Permission denied (you must
be root)` even though we're chroot'd as root — the default `kubectl
debug` profile doesn't grant full `NET_ADMIN`/netfilter access. To
actually use `iptables`, add a broader profile:
`kubectl debug node/<name> --profile=general -it -- chroot /host bash`.

**Filesystem — where Kubernetes actually stores things**
```bash
ls /var/lib/kubelet/pods/                # one directory per pod -- real volume mounts, mounted secrets as plain files
ls /var/log/pods/ /var/log/containers/   # raw log files, same source kubectl logs reads
```

**Resources — what a pod's requests/limits actually become**
```bash
cat /sys/fs/cgroup/.../memory.max   # the literal cgroup enforcing a pod's memory limit
top / ps aux                        # every container is just an OS process from here
```

**The one thing to be careful about**: you have real root on a real
node. Reading/inspecting anything above is safe to do freely — just
don't kill the `kubelet` systemd unit, edit the `iptables` rules
kube-proxy manages, or delete anything under `/var/lib/kubelet/` or
`/etc/kubernetes/` unless you specifically want to watch the node break
(on a solo-exploration 2-node cluster, that's actually a legitimate,
educational thing to try once).

## Cleanup — do this every time

`kubectl debug node` schedules a real pod (`node-debugger-<node>-<random>`)
on the node and does **not** delete it when you exit the shell. Left
alone, these accumulate.

Check what's sitting around:

```bash
kubectl get pods -A | grep node-debugger
```

Delete one by name:

```bash
kubectl delete pod <node-debugger-pod-name> -n default
```

Delete all of them at once:

```bash
kubectl get pods -n default -o name | grep node-debugger | xargs -r kubectl delete -n default
```

## `az vmss run-command invoke` — the one-shot alternative

No shell, but no `kubectl debug` pod to clean up either — good for a
single command:

```bash
az vmss list --resource-group "$(terraform output -raw node_resource_group)" --query "[].name" -o tsv
az vmss list-instances --resource-group "$(terraform output -raw node_resource_group)" \
  --name <vmss-name> --query "[].instanceId" -o tsv

az vmss run-command invoke \
  --resource-group "$(terraform output -raw node_resource_group)" \
  --name <vmss-name> \
  --instance-id <instance-id> \
  --command-id RunShellScript \
  --scripts "hostname && uptime"
```
