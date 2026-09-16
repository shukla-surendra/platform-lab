# Plugins and add-ons

What "plugin" and "add-on" actually mean in Kubernetes, the full list of
each, and — the part people most often get tangled on — how both relate
to the CRD+operator mechanism this repo builds from scratch in
`aks_crd_operator/`. Conceptual reference; verify anything version-specific
against a live cluster (`kubectl get pods -n kube-system`,
`kubectl get csidrivers`, `kubectl api-resources`) the way
`aks_crd_operator/docs/qna.md` does for its own claims.

Read in order:

1. [`01-first-principles.md`](./01-first-principles.md) — what a plugin
   is (an implementation of a Kubernetes-defined interface), what an
   add-on is (a much looser term), and why they're not the same thing —
   with embedded Q&A checkpoints.
2. [`02-plugin-interfaces-reference.md`](./02-plugin-interfaces-reference.md)
   — the full list of actual plugin interfaces (CNI, CSI, CRI, device
   plugins, scheduler extensions, the cloud-provider interface,
   admission webhooks) with real examples.
3. [`03-addons-reference.md`](./03-addons-reference.md) — the full,
   broader ecosystem add-on list (DNS, ingress, service mesh, certs,
   monitoring, GitOps, backup, autoscaling, policy, secrets), each tagged
   with which mechanism it actually uses.
4. [`04-relation-to-crd-and-operator.md`](./04-relation-to-crd-and-operator.md)
   — the direct comparison: what each mechanism answers, where they
   overlap in one add-on, and why neither can substitute for the other.
5. [`05-device-plugin-deep-dive.md`](./05-device-plugin-deep-dive.md) — one
   plugin interface from #2, taken all the way down: the actual gRPC
   contract (`Registration`, `ListAndWatch`, `Allocate`) and exactly what
   the NVIDIA device plugin does on each side of it.
6. [`FAQ.md`](./FAQ.md) — common questions, short-form, each pointing back
   into the fuller explanation.
