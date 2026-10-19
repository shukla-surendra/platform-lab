# --- Build stage: full Go toolchain ------------------------------------------
FROM golang:1.27-alpine AS build
WORKDIR /src

# Copy only go.mod/go.sum first so the dependency download is cached as its
# own layer -- code changes don't re-download modules.
COPY go.mod go.sum ./
RUN go mod download

COPY . .
ARG VERSION=dev
# CGO_ENABLED=0 -> fully static binary, runs on an image with no libc.
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w -X main.version=${VERSION}" -o /out/api ./cmd/api

# --- Runtime stage: just the binary (~15 MB image) ----------------------------
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/api /api
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/api"]
