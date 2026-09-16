# 5. The controller: Reconcile

[`internal/controller/webapp_controller.go`](../operators/webapp-operator/internal/controller/webapp_controller.go)
is the operator half of the pattern — the watch-reconcile loop referenced in
`k8s_explorer/docs/crds-and-operators.md`. This doc explains the choices in
that file, not just what it does.

## `Reconcile` is called for more than just "a WebApp changed"

```go
func (r *WebAppReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&webappv1alpha1.WebApp{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Complete(r)
}
```

`.For(&WebApp{})` watches `WebApp` objects directly. `.Owns(...)` watches
Deployments and Services *that this controller created* (identified by owner
reference, set below) and re-triggers `Reconcile` for the owning `WebApp`
whenever one of them changes — including changes made outside the operator
entirely. Run `kubectl scale deploy hello-webapp --replicas=5` after step 7
and watch it get reverted back to `spec.replicas` within seconds: that's this
`Owns()` watch firing, not a poll loop. This self-healing behavior is the
entire point of running a controller instead of a one-shot script that
creates the Deployment once.

## Reconcile is a function of desired state, called repeatedly

```go
func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	var webApp webappv1alpha1.WebApp
	if err := r.Get(ctx, req.NamespacedName, &webApp); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}
	if err := r.reconcileDeployment(ctx, &webApp); err != nil { ... }
	if err := r.reconcileService(ctx, &webApp); err != nil { ... }
	if err := r.updateStatus(ctx, &webApp); err != nil { ... }
	...
}
```

No `switch` on "was this a create or an update event" — every call re-derives
the Deployment and Service the `WebApp` *should* look like right now and
reconciles reality toward that, via `controllerutil.CreateOrUpdate`. This is
the same idempotent, level-triggered design every built-in Kubernetes
controller uses (a Deployment's own controller works identically against
ReplicaSets). Writing Reconcile as "diff current event type, apply a delta"
instead is a common first-operator mistake — it silently breaks the moment
an event is missed or delivered twice, both of which controller-runtime's
own watch mechanism does not guarantee against.

## `client.IgnoreNotFound` and the missing finalizer

```go
if err := r.Get(ctx, req.NamespacedName, &webApp); err != nil {
	return ctrl.Result{}, client.IgnoreNotFound(err)
}
```

When a `WebApp` is deleted, `r.Get` returns a NotFound error; `IgnoreNotFound`
turns that into "nothing to do" rather than an error to retry. There's no
finalizer and no explicit deletion-handling branch because cleanup is
delegated entirely to Kubernetes garbage collection — see the next section.

## Owner references are what make deletion "just work"

```go
return controllerutil.SetControllerReference(webApp, deployment, r.Scheme)
```

Set on both the Deployment and the Service inside `reconcileDeployment` /
`reconcileService`. This writes an `ownerReferences` entry pointing back at
the `WebApp`, which is what Kubernetes' own garbage collector (not this
operator) uses to cascade-delete the Deployment and Service the instant the
`WebApp` is deleted — confirm with `kubectl get deploy,svc -l
app.kubernetes.io/instance=hello-webapp` immediately after `kubectl delete
webapp hello-webapp` in step 7 and watch them disappear without the operator
doing anything explicit. It's also what makes `kubectl get deploy
hello-webapp -o yaml | grep -A3 ownerReferences` point back at the `WebApp`,
and what `kubectl describe webapp hello-webapp`'s events would show a
`BlockOwnerDeletion` conflict for, if you tried to delete the Deployment
while a foreground-deletion policy was active elsewhere.

## Labels: three different jobs, set in three different places

`labelsFor(webApp)` is used for all of: the Deployment's `spec.selector` +
pod template labels (so the ReplicaSet/Pods it creates match), the Service's
`spec.selector` (so it routes to those same Pods), *and* — easy to miss —
`deployment.Labels` / `service.Labels` on the objects' own metadata. That
third one doesn't affect routing or scheduling at all; it's what makes
`kubectl get deploy,svc -l app.kubernetes.io/instance=hello-webapp` (used
throughout step 7) find the Deployment and Service in the first place.
Setting `spec.selector` alone gets you a working app with nothing
`kubectl -l` can find — a real first-run gap this tutorial's own deployment
against AKS caught, not a hypothetical.

## Status updates go through the status subresource client

```go
func (r *WebAppReconciler) updateStatus(ctx context.Context, webApp *webappv1alpha1.WebApp) error {
	...
	webApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
	return r.Status().Update(ctx, webApp)
}
```

`r.Status().Update` — not `r.Update` — because of the
`+kubebuilder:subresource:status` marker from step 4: with that marker set, a
plain `r.Update(ctx, webApp)` would silently be rejected from writing
`status` at all (spec and status are different API endpoints once the
subresource is enabled). Using the wrong client method here is the second
most common first-operator bug after forgetting `make generate`.

## RBAC markers

```go
// +kubebuilder:rbac:groups=webapp.platformlab.dev,resources=webapps,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services,verbs=get;list;watch;create;update;patch;delete
```

Compiled by `make manifests` (step 3) into `config/rbac/role.yaml` — the
ClusterRole the operator's own ServiceAccount runs as. Miss a verb here (e.g.
forget `patch` on `deployments`) and `reconcileDeployment`'s
`CreateOrUpdate` call fails at runtime with a `Forbidden` error visible in
`kubectl logs deploy/webapp-operator-controller-manager -n
webapp-operator-system` — worth knowing as the first place to look if step 7
shows a `WebApp` object with no Deployment ever appearing.
