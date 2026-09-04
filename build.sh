#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
IMAGE="ghcr.io/yangchuansheng/eaglerx1.8server"
TAG="${1:-latest}"
FULL="${IMAGE}:${TAG}"

python3 "${ROOT}/script/sync_admin_assets.py"
echo ">>> Building ${FULL} ..."
docker build -t "${FULL}" "${ROOT}"

echo ">>> Done: ${FULL}"
docker images "${IMAGE}" --format "table {{.Tag}}\t{{.Size}}"

if [ "$2" = "push" ]; then
    docker push "${FULL}"
    echo ">>> Pushed: ${FULL}"
fi
