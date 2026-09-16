# 4. Watch and list

Every controller in this repo — `webapp-operator`'s `controller-runtime`
manager, `greeting-operator`'s kopf loop, `kube-controller-manager` and
`kube-scheduler` themselves — is built on the same primitive: **list, then
watch.**

## The pattern

1. **List** — `GET /apis/<group>/<version>/namespaces/<ns>/<resource>` once,
   to get the full current state plus a `resourceVersion` (etcd's revision
   number at the moment of the list — an opaque, monotonically increasing
   marker, not a wall-clock timestamp).
2. **Watch** — `GET .../<resource>?watch=true&resourceVersion=<that value>`,
   which doesn't return a normal response — the connection stays open and
   the API server streams newline-delimited JSON events (`ADDED`,
   `MODIFIED`, `DELETED`) as they happen, starting from that
   `resourceVersion` forward.

This is exactly why `controller-runtime`'s `SetupWithManager` (`For(...)`,
`Owns(...)` in `aks_crd_operator/operators/webapp-operator/internal/controller/webapp_controller.go`)
and kopf's `@kopf.on.create/update` decorators
(`aks_crd_operator/operators/webapp-operator-python/operator.py`) never
poll — both set up exactly this list-then-watch call per resource type
they care about, and get called back only when something actually
changes.

## Why list-then-watch, not just watch

A long-lived watch connection can drop (network blip, API server
restart, load balancer rebalancing). On reconnect, the client needs to
know it didn't miss anything in between — replaying the full list is the
simple, correct way to guarantee that, at the cost of doing it more than
strictly necessary. `resourceVersion` is what makes an *incremental*
recovery possible instead of a full list every time: reconnect with
`resourceVersion=<last seen>` and the API server resumes streaming from
there, backed by etcd's own revision history — as long as that history
hasn't been compacted away yet (etcd only retains a limited window of old
revisions; a watch reconnecting with a `resourceVersion` too old for etcd
to still have gets a `410 Gone` and has to fall back to a fresh list).

## Bookmarks

A `BOOKMARK` event type exists purely to advance `resourceVersion` without
sending a real object change — useful when a resource is quiet for a long
time and a client wants an up-to-date `resourceVersion` to reconnect from
without a full re-list. Opt-in via `allowWatchBookmarks=true` on the watch
request (visible in the raw watch URL kopf and client-go both issue).

## Where each operator in this repo actually does this

- **`webapp-operator`** — `client-go`'s **informer** (wrapped by
  `controller-runtime`'s manager) does list-then-watch once per watched
  GVK and maintains a local, continuously-updated cache; `Reconcile` reads
  from that cache, never hitting the API server directly for a `Get` in
  the common path. `Owns(&Deployment{})`/`Owns(&Service{})` are two more
  informers, one per owned type — this is the literal mechanism behind
  the "event-driven, near-instant" self-heal described throughout
  `aks_crd_operator/docs/qna.md`.
- **`webapp-operator-python`/`greeting-operator`** — kopf runs its own
  list-then-watch loop per decorated resource, same pattern, no local
  cache layer as deliberately minimal as `controller-runtime`'s informer
  cache. The `@kopf.timer(interval=30)` self-heal mechanism documented in
  `aks_crd_operator/docs/qna.md` exists specifically because kopf doesn't
  set up an additional owned-resource watch by default the way
  `Owns(...)` does — it's polling on a timer instead of an event stream
  for that specific gap.
- **`kube-controller-manager`'s built-in controllers** (Deployment →
  ReplicaSet → Pod, the whole built-in reconciliation chain) — same
  informer pattern, at the scale of the entire cluster instead of one CRD.

## Why this all traces back to `01-architecture-and-role.md`

None of this would be a single, consistent mechanism if anything other
than `kube-apiserver` could write to etcd — every watch is really "notify
me when *the API server's own write path* touches this resource," which is
only a coherent guarantee because that write path is the *only* write
path.
