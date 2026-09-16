#!/bin/bash
# Supervises the game server inside a tmux pane.
#
# The Server Management Panel shipped in the runtime bundle probes readiness and
# restarts the game server through tmux, so the pane has to outlive a crashed
# process. systemd supervises this script and restarts the unit once the pane
# stays dead.

set -euo pipefail

APP_DIR=/opt/eaglercraft
CONF="${APP_DIR}/bin/tmux.conf"
SESSION=${TMUX_SESSION:-mcserver}
WINDOW=paper
TARGET="${SESSION}:${WINDOW}.0"

tmux -f "$CONF" kill-server 2>/dev/null || true
tmux -f "$CONF" new-session -d -s "$SESSION" -n "$WINDOW" -c "${APP_DIR}/server" 'exec ./run.sh'

pane_dead() {
  [ "$(tmux display-message -p -t "$TARGET" '#{pane_dead}' 2>/dev/null || echo 1)" = 1 ]
}

shutdown() {
  if ! pane_dead; then
    tmux send-keys -t "$TARGET" 'stop' C-m
    for _ in $(seq 30); do
      pane_dead && break
      sleep 1
    done
  fi
  tmux kill-server 2>/dev/null || true
}
trap shutdown TERM INT

while true; do
  if pane_dead; then
    sleep 10
    pane_dead && exit 1
  fi
  sleep 2
done
