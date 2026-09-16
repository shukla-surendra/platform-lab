# 3. Scaffolding with Kubebuilder

`api/v1alpha1/*.go`, `internal/controller/webapp_controller.go`, `main.go`,
`Dockerfile`, and `config/samples/*.yaml` in
[`operators/webapp-operator/`](../operators/webapp-operator) are checked into
this repo already — hand-written for this tutorial, ready to read without
installing anything.

Everything else Kubebuilder normally generates (`go.mod`/`go.sum`,
`PROJECT`, `Makefile`, `config/crd/bases/*.yaml`, `config/rbac/*.yaml`,
`config/manager/*.yaml`, `config/default/kustomization.yaml`,
`hack/boilerplate.go.txt`) is **not** checked in. Those files are the direct
output of running the tool below against a specific Kubebuilder/
controller-runtime version — hand-typing them risks drifting from whatever
version you actually install, and the CRD YAML in particular (`config/crd/bases`)
is auto-generated *from* the `+kubebuilder:validation` markers already in
`webapp_types.go`, so writing it by hand would just be re-deriving something
the tool does correctly for free. Run the commands once and you have a real,
version-matched scaffold to drop the hand-written files into.

## Install

```bash
go install sigs.k8s.io/kubebuilder/v4/cmd/kubebuilder@latest
kubebuilder version
```

## Scaffold the project

```bash
mkdir -p /tmp/webapp-operator && cd /tmp/webapp-operator
kubebuilder init --domain platformlab.dev --repo platformlab.dev/webapp-operator
kubebuilder create api --group webapp --version v1alpha1 --kind WebApp --resource --controller
```

Answer `y` to both "Create Resource" and "Create Controller" prompts if
asked. This generates `go.mod`, `main.go`, `api/v1alpha1/webapp_types.go`,
`api/v1alpha1/groupversion_info.go`, `internal/controller/webapp_controller.go`,
`config/crd/`, `config/rbac/`, `config/manager/`, `config/samples/`, and a
`Makefile` with `docker-build`, `deploy`, `manifests`, etc. targets already
wired to those paths.

## Drop in the hand-written files

Copy this repo's versions over the generated stubs — they contain the same
struct/function names the scaffold created, just with the tutorial's actual
fields and Reconcile logic filled in instead of the placeholder `Foo string`
field and empty `Reconcile` body:

```bash
cp k8s/aks_crd_operator/operators/webapp-operator/api/v1alpha1/webapp_types.go \
   /tmp/webapp-operator/api/v1alpha1/webapp_types.go

cp k8s/aks_crd_operator/operators/webapp-operator/internal/controller/webapp_controller.go \
   /tmp/webapp-operator/internal/controller/webapp_controller.go

cp k8s/aks_crd_operator/operators/webapp-operator/config/samples/webapp_v1alpha1_webapp.yaml \
   /tmp/webapp-operator/config/samples/webapp_v1alpha1_webapp.yaml
```

Leave the scaffold's own `main.go`, `groupversion_info.go`, `Dockerfile`,
`Makefile`, and everything under `config/` as generated — this repo's
`main.go`/`Dockerfile`/`groupversion_info.go` are reference copies matching
what the scaffold already produces, useful for reading without installing
Kubebuilder, not meant to overwrite a real scaffold that may generate
slightly different boilerplate on a newer version.

## Regenerate CRD YAML + RBAC from the markers

The `+kubebuilder:validation:*` comments in `webapp_types.go` and the
`+kubebuilder:rbac:*` comments in `webapp_controller.go` are read by
`controller-gen` (bundled via the Makefile), not by Go itself — they're
structured comments, not compiled code:

```bash
cd /tmp/webapp-operator
make manifests   # writes config/crd/bases/webapp.platformlab.dev_webapps.yaml
                  # and config/rbac/role.yaml from the marker comments
make generate     # writes zz_generated.deepcopy.go (DeepCopyObject etc.)
```

`make generate` is what makes `WebApp` satisfy `runtime.Object` (needed for
`SchemeBuilder.Register` in `groupversion_info.go` to compile) — skipping it
is the most common "why won't this build" moment on a first Kubebuilder
project.

## Sanity check

```bash
go build ./...
```

Should compile cleanly against the go.mod this step generated. If it
doesn't, it's almost always one of: `make generate` skipped (missing
DeepCopy methods), or the hand-copied controller file referencing a package
path that doesn't match `--repo` (`platformlab.dev/webapp-operator` — must
match exactly what you passed to `kubebuilder init`).
