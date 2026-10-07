# kubectl rollout cheat sheet

`kubectl rollout` manages the release history of a workload.

**Works on:** `Deployment`, `DaemonSet`, `StatefulSet`.
**Does NOT work on:** Pod, Service, ConfigMap, Job (no rollout concept).
Pause/resume is Deployment-only.

Examples use `deployment/nginx-deployment -n nginx-demo`.

## Commands

| Command | What it does |
|---|---|
| `kubectl rollout status deployment/nginx-deployment -n nginx-demo` | Watch a rollout until it finishes (or fails). Good in scripts and CI. |
| `kubectl rollout history deployment/nginx-deployment -n nginx-demo` | List past revisions. |
| `kubectl rollout history deployment/nginx-deployment -n nginx-demo --revision=2` | Show the full spec (image, labels) of one revision. |
| `kubectl rollout undo deployment/nginx-deployment -n nginx-demo` | Roll back to the previous revision. |
| `kubectl rollout undo deployment/nginx-deployment -n nginx-demo --to-revision=1` | Roll back to a specific revision. |
| `kubectl rollout restart deployment/nginx-deployment -n nginx-demo` | Recreate all Pods one by one with no spec change (e.g. to pick up a changed ConfigMap or a re-pulled image). |
| `kubectl rollout pause deployment/nginx-deployment -n nginx-demo` | Freeze the Deployment. Edits are queued, not rolled out. Deployment only. |
| `kubectl rollout resume deployment/nginx-deployment -n nginx-demo` | Release the queued changes in one rollout. Deployment only. |

## Typical flow

```bash
# 1. release a new version
kubectl set image deployment/nginx-deployment nginx=nginx:1.27 -n nginx-demo
#    (or edit image in deployment.yml and kubectl apply -f deployment.yml)

# 2. watch it
kubectl rollout status deployment/nginx-deployment -n nginx-demo

# 3. it broke? go back
kubectl rollout undo deployment/nginx-deployment -n nginx-demo
```

## Good to know

- **What creates a revision:** only changes under `spec.template` (image, env, ports...). Changing `replicas` does NOT.
- **Revision = ReplicaSet.** Each revision is one old ReplicaSet kept at 0 replicas.
  See them: `kubectl get rs -n nginx-demo`.
- **How many are kept:** `spec.revisionHistoryLimit` (default 10).
- **CHANGE-CAUSE column is empty by default.** Fill it with:
  `kubectl annotate deployment/nginx-deployment kubernetes.io/change-cause="upgrade to 1.27" -n nginx-demo`
- **Undo is itself a new revision.** Rolling back from rev 3 to 1 creates rev 4 (a copy of 1).
- **Pace of a rollout** is set by `spec.strategy.rollingUpdate` (`maxSurge`, `maxUnavailable`).
- **Stuck rollout:** `rollout status` times out after `spec.progressDeadlineSeconds` (default 600s).
  Check `kubectl describe deployment ...` and `kubectl get pods`, then `rollout undo`.
- **Pause use case:** make several edits (image + env + resources), then `resume` so they ship as one revision instead of three.
