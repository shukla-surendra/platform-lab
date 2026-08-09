IMAGE   ?= rust-sqlite-api
VERSION ?= 0.2.0
PORT    ?= 8080

.PHONY: build build-amd64 check dev dev-release dev-reset verify run run-amd64 stop stop-amd64 logs shell smoke otlp size clean push push-dry

# ---------------------------------------------------------------------------
# Local loop:  make dev  (terminal 1)  →  make verify  (terminal 2)  →  make run
# ---------------------------------------------------------------------------

# Run natively, no container. The image default DATABASE_PATH=/data/app.db is
# correct inside the image and unwritable on macOS, so dev keeps its database
# in ./data (gitignored) — this is why bare `cargo run` does not work.
dev:
	DATABASE_PATH=./data/app.db BIND_ADDR=127.0.0.1:$(PORT) RUST_LOG=info cargo run

# Same, with release optimisations — use this before trusting any timing you
# measure. A debug build is roughly an order of magnitude slower and will make
# you "fix" a bottleneck that does not exist in the image.
dev-release:
	DATABASE_PATH=./data/app.db BIND_ADDR=127.0.0.1:$(PORT) RUST_LOG=info cargo run --release

# Wipe local state. Retention and dedupe both behave differently on a warm
# database, so start cold whenever a result looks confusing.
dev-reset:
	rm -rf ./data

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

run: build
	docker run -d --name $(IMAGE) -p $(PORT):8080 -v $(IMAGE)-data:/data $(IMAGE):$(VERSION)

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
	  -p $(PORT):8080 -v $(IMAGE)-amd64-data:/data $(IMAGE):$(VERSION)-amd64

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
	curl -fsS localhost:$(PORT)/healthz >/dev/null && echo "healthz  ok"; \
	curl -fsS localhost:$(PORT)/readyz  >/dev/null && echo "readyz   ok"; \
	id=$$(curl -fsS -X POST localhost:$(PORT)/api/notes \
	     -H 'content-type: application/json' \
	     -d '{"title":"smoke","body":"from make"}' | sed 's/.*"id":\([0-9]*\).*/\1/'); \
	echo "create   ok (id=$$id)"; \
	curl -fsS localhost:$(PORT)/api/notes/$$id >/dev/null && echo "get      ok"; \
	curl -fsS localhost:$(PORT)/api/notes      >/dev/null && echo "list     ok"; \
	test "$$(curl -s -o /dev/null -w '%{http_code}' -X DELETE localhost:$(PORT)/api/notes/$$id)" = 204 \
	     && echo "delete   ok"; \
	test "$$(curl -s -o /dev/null -w '%{http_code}' localhost:$(PORT)/api/notes/$$id)" = 404 \
	     && echo "404      ok"

# Push the sample OTLP payloads, then read them back through the query API.
otlp:
	@ENDPOINT=http://localhost:$(PORT) ./testdata/send.sh
	@sleep 1
	@echo; echo "--- stored ---";      curl -fsS localhost:$(PORT)/api/summary
	@echo; echo "--- errors ---";      curl -fsS 'localhost:$(PORT)/api/logs?severity=error'
	@echo; echo "--- slow traces ---"; curl -fsS 'localhost:$(PORT)/api/traces?min_duration_ms=50'
	@echo

# Publish multi-arch to Docker Hub. Delegates to scripts/publish.sh, which
# gates the push behind fmt/clippy/build, a real acceptance run against the
# built image, and a refusal to overwrite an existing remote tag.
#
#   make push TAG=0.2.0
#   make push TAG=0.2.0 PUSH_ARGS=--latest
#   make push-dry TAG=0.2.0
push:
	@test -n "$(TAG)" || { echo "usage: make push TAG=<tag>"; exit 1; }
	./scripts/publish.sh $(TAG) $(PUSH_ARGS)

push-dry:
	@test -n "$(TAG)" || { echo "usage: make push-dry TAG=<tag>"; exit 1; }
	./scripts/publish.sh $(TAG) --dry-run $(PUSH_ARGS)

clean: stop
	-docker volume rm $(IMAGE)-data
	cargo clean
