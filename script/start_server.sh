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

VERSION="${MINECRAFT_VERSION}"
VALID_VERSIONS=("1.8" "1.12")

if [[ ! " ${VALID_VERSIONS[*]} " =~ " ${VERSION} " ]]; then
    echo "[start] ERROR: Invalid MINECRAFT_VERSION '${VERSION}'. Valid: 1.8, 1.12"
    exit 1
fi

if [ "${APP_DIR}" != "${IMAGE_APP_DIR}" ]; then
    mkdir -p "${APP_DIR}"
    if [ ! -f "${APP_DIR}/script/start_server.sh" ]; then
        if [ -n "$(find "${APP_DIR}" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
            echo "[start] ERROR: mounted app dir is non-empty and incomplete: ${APP_DIR}"
            echo "[start]        use an empty directory or restore a complete application directory"
            exit 1
        fi
        echo "[start] initializing mounted app dir: ${APP_DIR} <- ${IMAGE_APP_DIR}"
        cp -a "${IMAGE_APP_DIR}/." "${APP_DIR}/"
    fi
fi

SERVER_DIR="${APP_DIR}/server-${VERSION}"
WEB_DIR="${APP_DIR}/web-${VERSION}"
ACTIVE_SERVER_DIR="${APP_DIR}/server"
ACTIVE_WEB_DIR="${APP_DIR}/web"

echo "[start] MINECRAFT_VERSION=${VERSION}"

if [ ! -d "${WEB_DIR}" ] || [ ! -d "${SERVER_DIR}" ] \
    || [ ! -f "${APP_DIR}/bungee/run.sh" ] \
    || [ ! -f "${APP_DIR}/script/http_server.py" ]; then
    echo "[start] ERROR: application directory is incomplete: ${APP_DIR}"
    exit 1
fi

safe_link_dir() {
    local source="$1"
    local target="$2"
    if [ -L "${target}" ]; then
        rm -f "${target}"
    elif [ -e "${target}" ] && [ ! -d "${target}" ]; then
        echo "[start] ERROR: ${target} exists as a real file; refusing to replace it with a symlink"
        exit 1
    elif [ -d "${target}" ]; then
        if [ -n "$(ls -A "${target}" 2>/dev/null)" ]; then
            echo "[start] ERROR: ${target} exists as a real directory; refusing to replace it with a symlink"
            echo "[start]        remove/rename that directory or use a clean full-dir mount"
            exit 1
        fi
        rmdir "${target}"
    fi
    ln -sfn "${source}" "${target}"
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

# The configured data root is shared by the full-runtime mount and the legacy
# world-only mount. Each selected Minecraft version gets an isolated plugin
# repository beneath it.
PERSISTENT_DATA_ROOT="${PERSISTENT_DATA_ROOT:-${SERVER_DATA_DIR:-${APP_DIR}/server-data}}"
PLUGIN_REPOSITORY_DIR="${PERSISTENT_DATA_ROOT}/plugins-${VERSION}"
python3 "${APP_DIR}/script/plugin_repository.py" \
    --source "${ACTIVE_SERVER_DIR}/plugins" \
    --repository "${PLUGIN_REPOSITORY_DIR}" \
    --version "${VERSION}"
echo "[start] plugin repository ready for Minecraft ${VERSION}"

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
SERVER_DATA_DIR="${PERSISTENT_DATA_ROOT}"
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
        ln -sfn "${source_path}" "${ACTIVE_SERVER_DIR}/${target_name}"
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

TMUX_SESSION="${TMUX_SESSION:-mcserver}"
BUNGEE_PANE=""
SERVER_PANE=""
export TMUX_SESSION

HTTP_PID=""
SHUTTING_DOWN=0

pane_is_dead() {
    local state
    if ! state="$(tmux display-message -p -t "$1" '#{pane_dead}' 2>/dev/null)"; then
        return 0
    fi
    [ "${state}" = "1" ]
}

wait_for_pane_stop() {
    local pane="$1"
    local timeout="$2"
    local elapsed=0
    while [ "${elapsed}" -lt "${timeout}" ]; do
        if pane_is_dead "${pane}"; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

wait_for_port() {
    local host="$1"
    local port="$2"
    local timeout="$3"
    local elapsed=0
    while [ "${elapsed}" -lt "${timeout}" ]; do
        if pane_is_dead "${BUNGEE_PANE}"; then
            return 1
        fi
        if (echo >"/dev/tcp/${host}/${port}") >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

shutdown_services() {
    local exit_code="${1:-0}"
    if [ "${SHUTTING_DOWN}" -eq 1 ]; then
        return
    fi
    SHUTTING_DOWN=1
    trap - TERM INT
    set +e
    echo "[start] stopping services"
    if ! pane_is_dead "${SERVER_PANE}"; then
        tmux send-keys -t "${SERVER_PANE}" "stop" C-m >/dev/null 2>&1
        wait_for_pane_stop "${SERVER_PANE}" 30
    fi
    if ! pane_is_dead "${BUNGEE_PANE}"; then
        tmux send-keys -t "${BUNGEE_PANE}" "end" C-m >/dev/null 2>&1
        wait_for_pane_stop "${BUNGEE_PANE}" 10
    fi
    tmux kill-session -t "${TMUX_SESSION}" >/dev/null 2>&1
    if [ -n "${HTTP_PID}" ] && kill -0 "${HTTP_PID}" 2>/dev/null; then
        kill "${HTTP_PID}" >/dev/null 2>&1
        wait "${HTTP_PID}" 2>/dev/null
    fi
    exit "${exit_code}"
}

trap 'shutdown_services 0' TERM INT

BUNGEE_PANE="$(tmux new-session -d -P -F '#{pane_id}' -s "${TMUX_SESSION}" -n services)"
tmux set-window-option -t "${BUNGEE_PANE}" remain-on-exit on
tmux respawn-pane -k -t "${BUNGEE_PANE}" "cd \"${APP_DIR}/bungee\"; exec ./run.sh"
if ! wait_for_port 127.0.0.1 5200 60; then
    echo "[start] ERROR: Bungee did not become ready on port 5200"
    shutdown_services 1
fi
export PAPER_STARTED_AT="$(date +%s)"
SERVER_PANE="$(tmux split-window -d -h -P -F '#{pane_id}' -t "${BUNGEE_PANE}" "cd \"${ACTIVE_SERVER_DIR}\"; exec ./run.sh")"
export TMUX_BUNGEE_PANE="${BUNGEE_PANE}" TMUX_SERVER_PANE="${SERVER_PANE}"

cd "${ACTIVE_WEB_DIR}"
python3 "${APP_DIR}/script/http_server.py" &
HTTP_PID=$!

while true; do
    if ! kill -0 "${HTTP_PID}" 2>/dev/null; then
        echo "[start] ERROR: HTTP service exited"
        shutdown_services 1
    fi
    if pane_is_dead "${BUNGEE_PANE}"; then
        echo "[start] ERROR: Bungee service exited"
        shutdown_services 1
    fi
    if pane_is_dead "${SERVER_PANE}"; then
        sleep 5
        if pane_is_dead "${SERVER_PANE}"; then
            echo "[start] ERROR: Paper service exited"
            shutdown_services 1
        fi
    fi
    sleep 2
done
