#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${APP_DIR:-${DEFAULT_APP_DIR}}"
IMAGE_APP_DIR="${IMAGE_APP_DIR:-${DEFAULT_APP_DIR}}"

if [ -z "${MINECRAFT_VERSION:-}" ]; then
    echo "[start] ERROR: MINECRAFT_VERSION is required. Use -e MINECRAFT_VERSION=1.8 or -e MINECRAFT_VERSION=1.12"
    exit 1
fi

if [ "${APP_DIR}" != "${IMAGE_APP_DIR}" ]; then
    mkdir -p "${APP_DIR}"
    if [ ! -f "${APP_DIR}/script/start_server.sh" ]; then
        echo "[start] initializing mounted app dir: ${APP_DIR} <- ${IMAGE_APP_DIR}"
        cp -a "${IMAGE_APP_DIR}/." "${APP_DIR}/"
    fi
fi

VERSION="${MINECRAFT_VERSION}"
VALID_VERSIONS=("1.8" "1.12")
SERVER_DIR="${APP_DIR}/server-${VERSION}"
WEB_DIR="${APP_DIR}/web-${VERSION}"
ACTIVE_SERVER_DIR="${APP_DIR}/server"
ACTIVE_WEB_DIR="${APP_DIR}/web"

echo "[start] MINECRAFT_VERSION=${VERSION}"

if [[ ! " ${VALID_VERSIONS[*]} " =~ " ${VERSION} " ]]; then
    echo "[start] ERROR: Invalid MINECRAFT_VERSION '${VERSION}'. Valid: 1.8, 1.12"
    exit 1
fi

if [ ! -d "${WEB_DIR}" ] || [ ! -d "${SERVER_DIR}" ]; then
    echo "[start] ERROR: Missing version directories: ${WEB_DIR}, ${SERVER_DIR}"
    exit 1
fi

safe_link_dir() {
    local source="$1"
    local target="$2"
    if [ -L "${target}" ]; then
        rm -f "${target}"
    elif [ -e "${target}" ] && [ ! -d "${target}" ]; then
        rm -f "${target}"
    elif [ -d "${target}" ]; then
        if [ -n "$(ls -A "${target}" 2>/dev/null)" ]; then
            echo "[start] ERROR: ${target} exists as a real directory; refusing to replace it with a symlink"
            echo "[start]        remove/rename that directory or use a clean full-dir mount"
            exit 1
        fi
        rmdir "${target}"
    fi
    ln -sfnT "${source}" "${target}"
}

read_server_property() {
    local key="$1"
    local file="${ACTIVE_SERVER_DIR}/server.properties"
    python3 - "${file}" "${key}" <<'PY'
import sys
path, key = sys.argv[1:]
prefix = key + '='
try:
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(prefix):
                print(line.split('=', 1)[1].strip())
                break
except FileNotFoundError:
    pass
PY
}

safe_link_dir "${WEB_DIR}" "${ACTIVE_WEB_DIR}"
safe_link_dir "${SERVER_DIR}" "${ACTIVE_SERVER_DIR}"
echo "[start] web/ -> web-${VERSION}, server/ -> server-${VERSION}"

echo -e "#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://account.mojang.com/documents/minecraft_eula).\n#$(date)\neula=true" > "${ACTIVE_SERVER_DIR}/eula.txt"

set_server_property() {
    local key="$1"
    local value="$2"
    local file="${ACTIVE_SERVER_DIR}/server.properties"
    python3 - "${file}" "${key}" "${value}" <<'PY'
import sys
path, key, value = sys.argv[1:]
prefix = key + '='
try:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
except FileNotFoundError:
    lines = []

updated = False
for i, line in enumerate(lines):
    if line.startswith(prefix):
        lines[i] = prefix + value + '\n'
        updated = True
        break
if not updated:
    lines.append(prefix + value + '\n')

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
PY
}

if [ -n "${RCON_PASSWORD}" ]; then
    echo "[start] RCON enabled via RCON_PASSWORD env var"
    set_server_property "enable-rcon" "true"
    set_server_property "rcon.password" "${RCON_PASSWORD}"
else
    echo "[start] RCON disabled (RCON_PASSWORD not set)"
    set_server_property "enable-rcon" "false"
fi

# Optional legacy world-only persistence. Full-dir bind mount is preferred:
#   -v /host/eaglerX-1.8-server:/eaglerX-1.8-server
SERVER_DATA_DIR="${SERVER_DATA_DIR:-${APP_DIR}/server-data}"
LEVEL_NAME="$(read_server_property "level-name")"
LEVEL_NAME="${LEVEL_NAME:-world}"
if [ -d "${SERVER_DATA_DIR}" ] && { [ -e "${SERVER_DATA_DIR}/${LEVEL_NAME}" ] || [ -e "${SERVER_DATA_DIR}/world" ]; }; then
    link_world_dir() {
        local source_name="$1"
        local fallback_name="$2"
        local target_name="$3"
        local source_path=""
        if [ -e "${SERVER_DATA_DIR}/${source_name}" ]; then
            source_path="${SERVER_DATA_DIR}/${source_name}"
        elif [ -n "${fallback_name}" ] && [ -e "${SERVER_DATA_DIR}/${fallback_name}" ]; then
            source_path="${SERVER_DATA_DIR}/${fallback_name}"
        else
            return 0
        fi
        if [ -d "${ACTIVE_SERVER_DIR}/${target_name}" ] && [ ! -L "${ACTIVE_SERVER_DIR}/${target_name}" ]; then
            echo "[start] WARN: skip legacy mount for ${target_name}; target is a real directory"
            return 0
        fi
        ln -sfnT "${source_path}" "${ACTIVE_SERVER_DIR}/${target_name}"
    }
    link_world_dir "${LEVEL_NAME}" "world" "${LEVEL_NAME}"
    link_world_dir "${LEVEL_NAME}_nether" "world_nether" "${LEVEL_NAME}_nether"
    link_world_dir "${LEVEL_NAME}_the_end" "world_the_end" "${LEVEL_NAME}_the_end"
    echo "[start] using persistent world from ${SERVER_DATA_DIR}/"
fi

TMUX_SOCKET_DIR="${TMUX_TMPDIR:-/tmp/eaglerx-tmux}"
mkdir -p "${TMUX_SOCKET_DIR}"
chmod 700 "${TMUX_SOCKET_DIR}"
export TMUX_TMPDIR="${TMUX_SOCKET_DIR}"

tmux new-session -d -s mcserver
tmux split-window -h
tmux send-keys -t mcserver:0.0 "cd \"${APP_DIR}/bungee\"; ./run.sh" C-m
tmux send-keys -t mcserver:0.1 "cd \"${ACTIVE_SERVER_DIR}\"; ./run.sh" C-m

cd "${ACTIVE_WEB_DIR}"
python3 "${APP_DIR}/script/http_server.py" &

tail -f /dev/null
