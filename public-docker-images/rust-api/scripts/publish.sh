#!/usr/bin/env bash
#
# Build and push rust-api to a public registry.
#
# Publishing is one-way: once a tag is pulled by anyone, deleting or moving it
# breaks them. So this script gates the push behind checks that are cheap to run
# and expensive to skip — static checks, a real acceptance run against the built
# image, and a refusal to silently overwrite a tag that already exists.
#
#   ./scripts/publish.sh 0.2.0
#   ./scripts/publish.sh 0.2.0 --latest
#   ./scripts/publish.sh dev-test --dry-run
#
set -euo pipefail

REPO="surendrashukla29/rust-api"
PLATFORMS="linux/amd64,linux/arm64"
TAG=""
ALSO_LATEST=0
DRY_RUN=0
FORCE=0
SKIP_VERIFY=0
TEST_PORT=18080

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

die()  { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
info() { printf '\033[36m==>\033[0m %s\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }

usage() {
  cat <<EOF
usage: $(basename "$0") <tag> [options]

  <tag>                 image tag, e.g. 0.2.0  (required — there is no default,
                        because a default tag is how you overwrite :latest by
                        accident)

options:
  --repo REPO           default: $REPO
  --platforms LIST      default: $PLATFORMS
  --latest              also push :latest pointing at this build
  --dry-run             run every check and the full build, but do not push
  --force               overwrite the remote tag if it already exists
  --skip-verify         skip the acceptance run (not recommended)
  -h, --help            this
EOF
  exit 0
}

[ $# -eq 0 ] && usage
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)       REPO="${2:?--repo needs a value}"; shift 2 ;;
    --platforms)  PLATFORMS="${2:?--platforms needs a value}"; shift 2 ;;
    --latest)     ALSO_LATEST=1; shift ;;
    --dry-run)    DRY_RUN=1; shift ;;
    --force)      FORCE=1; shift ;;
    --skip-verify) SKIP_VERIFY=1; shift ;;
    -h|--help)    usage ;;
    -*)           die "unknown option: $1" ;;
    *)            [ -n "$TAG" ] && die "tag given twice: '$TAG' and '$1'"; TAG="$1"; shift ;;
  esac
done

[ -n "$TAG" ] || die "no tag given. usage: $(basename "$0") <tag>"

# Docker's own grammar for a tag. Catches the common paste error of including
# the repo ("surendrashukla29/rust-api:1.0.0") as the tag.
[[ "$TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$ ]] \
  || die "invalid tag '$TAG' — pass only the tag, not repo:tag"

IMAGE="$REPO:$TAG"

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
info "pre-flight"

docker info >/dev/null 2>&1 || die "docker daemon is not running"
ok "docker daemon up"

# Fail here rather than after a multi-minute multi-arch build.
if ! grep -q '"https://index.docker.io/v1/"' ~/.docker/config.json 2>/dev/null \
   && [ -z "${DOCKER_PASSWORD:-}" ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    warn "not logged in to Docker Hub — fine for --dry-run"
  else
    die "not logged in to Docker Hub. run: docker login -u ${REPO%%/*}"
  fi
else
  ok "docker hub credentials present"
fi

# A tag that looks like a version must match the version actually being built,
# or the image lies about itself in its own OCI labels.
CARGO_VERSION="$(grep -m1 '^version = ' Cargo.toml | cut -d'"' -f2)"
if [[ "$TAG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && [ "$TAG" != "$CARGO_VERSION" ]; then
  die "tag '$TAG' does not match Cargo.toml version '$CARGO_VERSION'.
       bump Cargo.toml (and Cargo.lock, via cargo build) or pass a non-version tag."
fi
ok "version consistent (Cargo.toml = $CARGO_VERSION)"

# Overwriting a published tag is the single most disruptive thing this script
# can do — anyone who pinned it gets different bytes with no signal.
if docker manifest inspect "$IMAGE" >/dev/null 2>&1; then
  if [ "$FORCE" -eq 1 ]; then
    warn "$IMAGE already exists remotely — overwriting (--force)"
  else
    die "$IMAGE already exists in the registry.
       pushing again would silently change what that tag means for everyone
       who pinned it. use a new tag, or --force if you are certain."
  fi
else
  ok "$IMAGE is not taken"
fi

# ---------------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------------
info "static checks"
cargo fmt --check                      >/dev/null && ok "cargo fmt"
cargo clippy --all-targets -- -D warnings 2>/dev/null >/dev/null && ok "clippy (no warnings)"
cargo build --release --locked         >/dev/null 2>&1 && ok "release build (--locked)"

# ---------------------------------------------------------------------------
# Acceptance — build the real image for this host and run the full check
# against it. Publishing an image whose own tests fail is the failure this
# whole script exists to prevent.
# ---------------------------------------------------------------------------
if [ "$SKIP_VERIFY" -eq 1 ]; then
  warn "skipping acceptance run (--skip-verify)"
else
  info "acceptance run"
  CONTAINER="rsa-publish-check-$$"
  cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
  trap cleanup EXIT

  docker build -q --build-arg VERSION="$TAG" -t "rsa-publish-check:$TAG" . >/dev/null
  ok "image built for this host"

  # No volume: the service is stateless.
  docker run -d --name "$CONTAINER" -p "$TEST_PORT:8080" \
    "rsa-publish-check:$TAG" >/dev/null

  for _ in $(seq 1 30); do
    curl -fsS "http://localhost:$TEST_PORT/readyz" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -fsS "http://localhost:$TEST_PORT/readyz" >/dev/null 2>&1 \
    || { docker logs "$CONTAINER" | tail -20; die "container never became ready"; }
  ok "container ready"

  ENDPOINT="http://localhost:$TEST_PORT" ./scripts/verify.sh \
    || die "acceptance checks failed — not publishing"

  cleanup
  trap - EXIT
  docker rmi "rsa-publish-check:$TAG" >/dev/null 2>&1 || true
fi

# ---------------------------------------------------------------------------
# Build and push, multi-arch
# ---------------------------------------------------------------------------
TAG_ARGS=(-t "$IMAGE")
[ "$ALSO_LATEST" -eq 1 ] && TAG_ARGS+=(-t "$REPO:latest")

if [ "$DRY_RUN" -eq 1 ]; then
  info "dry run — building $PLATFORMS, not pushing"
  # Multi-platform results cannot be --load'ed into the local image store, so a
  # dry run builds to the cache only. It still proves both architectures
  # compile, which is the part a push would otherwise discover the hard way.
  docker buildx build --platform "$PLATFORMS" \
    --build-arg VERSION="$TAG" "${TAG_ARGS[@]}" .
  echo
  ok "dry run complete — nothing was pushed"
  # Not ${ALSO_LATEST:+...} — that tests for non-empty, and "0" is non-empty,
  # so it claimed :latest would be pushed on every run.
  if [ "$ALSO_LATEST" -eq 1 ]; then
    echo "  would have pushed: $IMAGE and $REPO:latest"
  else
    echo "  would have pushed: $IMAGE"
  fi
  exit 0
fi

info "building and pushing $PLATFORMS → $IMAGE"
docker buildx build --platform "$PLATFORMS" \
  --build-arg VERSION="$TAG" "${TAG_ARGS[@]}" --push .

# ---------------------------------------------------------------------------
# Confirm what actually landed. A push that "succeeded" but produced a
# single-arch manifest is a real and quiet failure mode.
# ---------------------------------------------------------------------------
info "verifying the published manifest"
PUBLISHED="$(docker manifest inspect "$IMAGE" \
  | grep -o '"architecture": "[a-z0-9]*"' | cut -d'"' -f4 | sort -u | grep -v unknown | paste -sd, -)"
echo "  architectures: $PUBLISHED"

for want in ${PLATFORMS//,/ }; do
  arch="${want#linux/}"
  case ",$PUBLISHED," in
    *",$arch,"*) ok "$arch present" ;;
    *) die "$arch missing from the published manifest" ;;
  esac
done

echo
ok "published $IMAGE"
echo "  docker pull $IMAGE"
if [ "$ALSO_LATEST" -eq 1 ]; then
  echo "  docker pull $REPO:latest"
fi

# Explicit, and not decoration. A trailing `[ cond ] && echo` becomes the
# script's exit status under `set -e`: when the condition is false the whole
# run reports failure despite having succeeded, and any CI step wrapping this
# goes red on a good push.
exit 0
