# 8. Cleanup

Order matters: remove the CRD before destroying the cluster if you ever plan
to reuse the resource group, otherwise skip straight to the Terraform
destroy since the whole cluster is going away anyway.

## Remove the operator and any WebApps

```bash
cd /tmp/webapp-operator
kubectl delete -f config/samples/webapp_v1alpha1_webapp.yaml --ignore-not-found
make undeploy       # removes the manager Deployment + RBAC
make uninstall      # removes the CRD itself
```

Deleting the CRD (`make uninstall`) cascades to delete every remaining
`WebApp` object in the cluster, which in turn cascades (via the owner
references from step 5) to their Deployments/Services — so `make uninstall`
alone is enough even if you skip the `kubectl delete -f` above. Doing both
here just makes the order of operations explicit.

## Destroy the cluster and registry

```bash
cd k8s/aks_crd_operator/infra
terraform destroy
```

Confirms the resource group name matches `rg-aks-crd-lab` before it deletes
anything — this resource group is dedicated to this tutorial (separate from
`rg-aks-dev` in `k8s/aks_setup`), so destroying it doesn't touch anything
else in this repo.

## Leftovers Terraform doesn't know about

- The image pushed to ACR in step 6 is deleted along with the registry by
  `terraform destroy` above — nothing extra to clean up there.
- The local `/tmp/webapp-operator` directory from step 3 is outside
  git and outside Terraform; delete it whenever, or keep it around to
  re-run `make deploy` against a freshly applied cluster next time.
