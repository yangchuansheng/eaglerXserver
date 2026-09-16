#!/bin/bash
# Snapshots the live world to /var/backups/eaglercraft and prunes old snapshots.
#
# Runs as the eaglercraft user so it can drive the tmux pane that supervises the
# game server and read the runtime directories that user owns.

set -euo pipefail

APP_DIR=/opt/eaglercraft
DEST=/var/backups/eaglercraft
KEEP_DAYS=7
TARGET=${TMUX_SERVER_PANE:-mcserver:paper.0}

# Plain "save-all" returns once the worlds are written. The "flush" variant
# wedges the 1.8.8 chunk I/O thread on Java 21: the server logs
# "All chunks are saved" in an endless loop and stops answering RCON.
if tmux send-keys -t "$TARGET" 'save-all' C-m 2>/dev/null; then
  sleep 5
fi

stamp=$(date -u +%Y%m%dT%H%M%SZ)
tar -czf "${DEST}/world-${stamp}.tar.gz" -C "${APP_DIR}/server" \
  world world_nether world_the_end
find "$DEST" -maxdepth 1 -type f -name 'world-*.tar.gz' -mtime "+${KEEP_DAYS}" -delete
