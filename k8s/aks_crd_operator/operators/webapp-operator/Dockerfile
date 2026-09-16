# Same shape as kubebuilder's default scaffold Dockerfile: static Go binary
# built in one stage, copied into a distroless image with no shell in the next.
FROM golang:1.23 AS builder
ARG TARGETOS=linux
ARG TARGETARCH=amd64
WORKDIR /workspace

COPY go.mod go.sum ./
RUN go mod download

COPY main.go main.go
COPY api/ api/
COPY internal/ internal/

RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -a -o manager main.go

FROM gcr.io/distroless/static:nonroot
WORKDIR /
COPY --from=builder /workspace/manager .
USER 65532:65532

ENTRYPOINT ["/manager"]
