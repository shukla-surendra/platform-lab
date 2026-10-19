IMAGE   ?= rust-api
VERSION ?= 1.0.0
PORT    ?= 8080

.PHONY: build build-amd64 check dev dev-release verify run run-amd64 stop stop-amd64 logs shell smoke logstorm size clean push push-dry

# ---------------------------------------------------------------------------
# Local loop:  make dev  (terminal 1)  →  make verify  (terminal 2)  →  make run
# ---------------------------------------------------------------------------

dev:
	BIND_ADDR=127.0.0.1:$(PORT) RUST_LOG=info cargo run

# Same, with release optimisations — use this before trusting any timing you
# measure. A debug build is roughly an order of magnitude slower and will make
# you "fix" a bottleneck that does not exist in the image.
dev-release:
	BIND_ADDR=127.0.0.1:$(PORT) RUST_LOG=info cargo run --release

# Full acceptance check against whatever is listening on $(PORT) — native or
# container, identical assertions. Non-zero exit means do not build the image.
verify:
	@ENDPOINT=http://localhost:$(PORT) ./scripts/verify.sh

# Static checks. Run before building the image, not after.
check:
	cargo fmt --check
	cargo clippy --all-targets -- -D warnings
	cargo build --release --locked

build:
	docker build --build-arg VERSION=$(VERSION) -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

# No volume: the service is stateless.
run: build
	docker run -d --name $(IMAGE) -p $(PORT):8080 $(IMAGE):$(VERSION)

# --- x86-64 --------------------------------------------------------------
# `docker build` always produces host-arch, silently. On an arm64 Mac that
# means `make run` gives you an arm64 image even if you needed amd64 — there
# is no warning, you just find out on the deployment target. These targets are
# explicit about it.
#
# Both build and run go through QEMU emulation here, so expect the build to
# take minutes rather than seconds and the runtime to be materially slower.
# Emulated timings say nothing about how the image performs on real amd64
# hardware; do not benchmark this.
#
# --load is required to get the result into `docker images` — buildx otherwise
# leaves it in the build cache. It only works for a single platform, which is
# why `push` (multi-arch) uses --push instead.
build-amd64:
	docker buildx build --platform linux/amd64 --load \
	  --build-arg VERSION=$(VERSION) -t $(IMAGE):$(VERSION)-amd64 .

run-amd64: build-amd64
	-docker rm -f $(IMAGE)-amd64
	docker run -d --name $(IMAGE)-amd64 --platform linux/amd64 \
	  -p $(PORT):8080 $(IMAGE):$(VERSION)-amd64

stop-amd64:
	-docker rm -f $(IMAGE)-amd64

stop:
	-docker rm -f $(IMAGE)

logs:
	docker logs -f $(IMAGE)

shell:
	docker exec -it $(IMAGE) /bin/sh

size:
	docker images $(IMAGE) --format '{{.Repository}}:{{.Tag}}\t{{.Size}}'

# Exercises every route and asserts the status codes, so a broken build fails
# here rather than in a browser.
smoke:
	@set -e; \
	curl -fsS localhost:$(PORT)/healthz  >/dev/null && echo "healthz       ok"; \
	curl -fsS localhost:$(PORT)/readyz   >/dev/null && echo "readyz        ok"; \
	curl -fsS localhost:$(PORT)/version  >/dev/null && echo "version       ok"; \
	curl -fsS localhost:$(PORT)/         >/dev/null && echo "landing page  ok"; \
	curl -fsS localhost:$(PORT)/api/test/uuid >/dev/null && echo "test/uuid     ok"; \
	test "$$(curl -s -o /dev/null -w '%{http_code}' localhost:$(PORT)/api/test/status/503)" = 503 \
	     && echo "test/status   ok"; \
	test "$$(curl -s -o /dev/null -w '%{http_code}' -X POST localhost:$(PORT)/api/test/echo -d '{}')" = 200 \
	     && echo "test/echo     ok"

# Fires a small log burst and prints the exact reference count to check a log
# pipeline against — see the note in the JSON response.
logstorm:
	@curl -fsS -X POST 'localhost:$(PORT)/debug/logstorm?count=50&tag=make-logstorm'

# Publish multi-arch to Docker Hub. Delegates to scripts/publish.sh, which
# gates the push behind fmt/clippy/build, a real acceptance run against the
# built image, and a refusal to overwrite an existing remote tag.
#
#   make push TAG=1.0.0
#   make push TAG=1.0.0 PUSH_ARGS=--latest
#   make push-dry TAG=1.0.0
push:
	@test -n "$(TAG)" || { echo "usage: make push TAG=<tag>"; exit 1; }
	./scripts/publish.sh $(TAG) $(PUSH_ARGS)

push-dry:
	@test -n "$(TAG)" || { echo "usage: make push-dry TAG=<tag>"; exit 1; }
	./scripts/publish.sh $(TAG) --dry-run $(PUSH_ARGS)

clean: stop
	cargo clean
