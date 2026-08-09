# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build a statically linked binary against musl.
#
# Alpine's Rust image targets musl, which links statically by default. That is
# what lets the runtime stage be a bare Alpine with no libc, no libgcc, and no
# libsqlite3 to keep patched — rusqlite's "bundled" feature compiles SQLite
# from its amalgamated C source straight into the binary.
# ---------------------------------------------------------------------------
FROM rust:1.97-alpine AS build

# musl-dev + build-base give the C toolchain that bundled SQLite needs.
RUN apk add --no-cache musl-dev build-base

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src

# Cache mounts keep the registry and target dir out of the image entirely, so
# a rebuild reuses compiled deps without a fat layer carrying them. They are
# scratch space for the RUN only — hence the explicit cp, because /app/target
# is unmounted the moment this instruction ends.
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    cargo build --release --locked && \
    cp /app/target/release/rust-sqlite-api /app/rust-sqlite-api

# ---------------------------------------------------------------------------
# Stage 2 — runtime.
#
# Alpine rather than scratch: ~8 MB buys a shell for `docker exec` debugging
# and a busybox wget for HEALTHCHECK, which a public image is more useful for
# having. Nothing from the build stage comes across except the binary.
# ---------------------------------------------------------------------------
FROM alpine:3.22 AS runtime

ARG VERSION=0.1.0
LABEL org.opencontainers.image.title="rust-sqlite-api" \
      org.opencontainers.image.description="Minimal Rust (axum) HTTP API with an embedded SQLite database" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/shukla-surendra/platform-lab"

# Run as a non-root user. /data is created and chowned here so a *named* volume
# inherits this ownership; a bind-mounted host directory does not, and must be
# chowned on the host to uid 10001 (see README §Persistence).
RUN addgroup -g 10001 -S app && \
    adduser -u 10001 -S app -G app && \
    mkdir -p /data && chown app:app /data

COPY --from=build /app/rust-sqlite-api /usr/local/bin/rust-sqlite-api

USER app
WORKDIR /data
VOLUME ["/data"]
EXPOSE 8080

ENV DATABASE_PATH=/data/app.db \
    BIND_ADDR=0.0.0.0:8080 \
    DB_POOL_SIZE=8 \
    RUST_LOG=info

# Hits /healthz, not /readyz — a liveness probe that fails on a busy database
# would restart the container without unlocking anything. See routes.rs.
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

# Exec form, so the binary is PID 1 and receives SIGTERM directly — the shell
# form would put /bin/sh at PID 1, which does not forward signals, and the
# graceful shutdown in main.rs would never fire.
ENTRYPOINT ["/usr/local/bin/rust-sqlite-api"]
