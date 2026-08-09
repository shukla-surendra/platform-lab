# public_docker_images

Container images built here are meant to be **published** — pushed to a public
registry (Docker Hub / GHCR) and pulled by someone who has never seen this repo.
That constraint is the point of keeping them separate from the rest of
`platform-lab`, where a Dockerfile only ever has to work on this laptop.

Anything in this folder is expected to be:

| Requirement | Why it matters once the image is public |
|---|---|
| **Multi-stage, minimal runtime** | Build toolchains in a shipped image are pure attack surface — nothing that compiled the binary belongs next to it in production. |
| **Non-root by default** | The puller does not know your uid. Root-by-default images get blocked outright by any cluster running a restricted `PodSecurity` policy. |
| **Pinned base tags** | `FROM rust:latest` makes the build unreproducible and silently changes the runtime under people who pinned *your* tag. |
| **Configured by environment** | A config file baked into the image needs a rebuild to change; env vars are the only knob a puller actually has. |
| **`HEALTHCHECK` + graceful SIGTERM** | Orchestrators assume both. Missing them shows up as flapping restarts and cut connections, blamed on the image. |
| **OCI labels** | `org.opencontainers.image.*` — source, version, licence. Registries and scanners read these. |
| **Multi-arch on push** | arm64 laptops and amd64 CI both pull the same tag; a single-arch image fails on half of them. |

## Images

| Image | What it is | Size | Status |
|---|---|---|---|
| [`rust-sqlite-api/`](rust-sqlite-api/) | OTLP-compatible collector for logs, metrics, and traces, backed by an embedded SQLite database on a volume. Rust + axum, statically linked. | 23.5 MB<br>(6.7 MB pulled) | **Published** → [`surendrashukla29/rust-sqlite-api:0.2.0`](https://hub.docker.com/r/surendrashukla29/rust-sqlite-api) · `amd64` + `arm64` · Helm chart and Grafana dashboard in [`deploy/`](rust-sqlite-api/deploy/) |

## Publishing

Each image directory carries `scripts/publish.sh`, driven by `make push TAG=<tag>`.
It builds `linux/amd64,linux/arm64` as a single OCI index and gates the push
behind checks — because publishing is one-way, and once a tag is pulled,
changing it breaks whoever pinned it:

| Gate | Why |
|---|---|
| Tag required, no default | A default tag is how you overwrite `:latest` by accident |
| Registry login checked first | Fails in a second, not after a multi-minute multi-arch build |
| Version-shaped tag must match `Cargo.toml` | Otherwise the image's own OCI labels lie about what it is |
| Remote tag must not already exist | Re-pushing silently changes what that tag means for everyone pinned to it |
| Full acceptance run against the built image | Publishing an image whose own tests fail is the failure this prevents |
| Published manifest re-inspected | A push that "succeeds" with a single-arch manifest is a real, quiet failure |

`make push-dry TAG=<tag>` runs all of it and stops short of the push.
