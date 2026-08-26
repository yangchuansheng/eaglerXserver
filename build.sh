#!/bin/bash
set -e
IMAGE="ghcr.io/yangchuansheng/eaglerx1.8server"
TAG="${1:-latest}"
FULL="${IMAGE}:${TAG}"

echo ">>> Building ${FULL} ..."
docker build -t "${FULL}" "$(dirname "$0")"

echo ">>> Done: ${FULL}"
docker images "${IMAGE}" --format "table {{.Tag}}\t{{.Size}}"

if [ "$2" = "push" ]; then
    docker push "${FULL}"
    echo ">>> Pushed: ${FULL}"
fi
