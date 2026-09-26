# One image for everything: feast CLI, feature server, init job, and the explore scripts.
FROM python:3.12-slim

ARG FEAST_VERSION=0.66.0
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FEAST_USAGE=False

# redis and postgres extras = the online and offline/registry backends used here;
# grpcio = needed by `feast ui` (registry REST routes import grpc)
RUN pip install "feast[redis,postgres,grpcio]==${FEAST_VERSION}" requests

WORKDIR /app
