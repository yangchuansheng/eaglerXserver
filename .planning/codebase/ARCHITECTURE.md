<!-- refreshed: 2026-08-20 -->
# Architecture

**Analysis Date:** 2026-08-20

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Docker runtime / host                    │
│              `Dockerfile`, `script/start_server.sh`         │
├──────────────────┬──────────────────┬───────────────────────┤
│ Eagler web client │ HTTP admin/API   │ Waterfall proxy       │
│ `web-1.8/`,       │ `script/http_    │ `bungee/`, port 5200  │
│ `web-1.12/`       │ server.py`, 5201 │                       │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Active runtime aliases                   │
│        `web/` → selected web tree; `server/` → selected jar │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Paper server and persistent world/plugin state               │
│ `server-1.8/`, `server-1.12/`, `server-data/`                │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Container image | Packages both server/client versions and installs the entrypoint | `Dockerfile` |
| Runtime selector | Validates version, initializes mounts, creates aliases, starts processes | `script/start_server.sh` |
| Waterfall proxy | Accepts Eagler WebSocket/HTTP traffic and routes to Paper | `bungee/bungee.jar`, `bungee/plugins/EaglercraftXBungee/listeners.yml` |
| Paper runtime | Runs Minecraft gameplay, plugins, worlds, and RCON | `server-1.8/run.sh`, `server-1.12/run.sh` |
| Admin bridge | Serves selected web files, exposes authenticated admin APIs, proxies Dynmap | `script/http_server.py` |
| Admin UI | Sends dashboard commands and renders runtime state | `web-1.8/admin.js`, `web-1.12/admin.js` |
| Seed native bridge | Exposes structure/spawn calculations from cubiomes to Python | `script/cubiomes_shim.c`, `script/libcubiomes_shim.so` |

## Pattern Overview

**Overall:** Containerized multi-version runtime with a proxy-fronted game server and a single Python control-plane process.

**Key Characteristics:**
- One image contains parallel `server-*` and `web-*` trees; `MINECRAFT_VERSION` selects one pair at startup.
- `tmux` owns two long-running Java panes: Bungee first, Paper second (`script/start_server.sh`).
- The admin bridge reads and writes Paper properties, sends RCON packets, reads world/player files, and optionally calls the native cubiomes library.

## Layers

**Deployment layer:**
- Purpose: Build the image and establish runtime paths.
- Location: `Dockerfile`, `build.sh`
- Contains: Base image, copied application tree, environment defaults, entrypoint.
- Depends on: Docker and the base Java image.
- Used by: `script/start_server.sh`.

**Process orchestration layer:**
- Purpose: Select a version and launch the service processes.
- Location: `script/start_server.sh`, `bungee/run.sh`, `server-1.8/run.sh`, `server-1.12/run.sh`
- Contains: Validation, symlinks, EULA/RCON property updates, tmux commands.
- Depends on: Bash, Python 3, tmux, Java.
- Used by: Docker `ENTRYPOINT`.

**Network gateway layer:**
- Purpose: Provide the public Eaglercraft endpoint and route clients to Minecraft.
- Location: `bungee/plugins/EaglercraftXBungee/listeners.yml`, `bungee/config.yml`
- Contains: Listener on port 5200, static web root, lobby route to `localhost:25565`, rate limits.
- Depends on: Waterfall and EaglercraftXBungee plugin.
- Used by: Browser clients.

**Control-plane layer:**
- Purpose: Serve the fallback/admin site and mediate privileged operations.
- Location: `script/http_server.py`
- Contains: Static files, `/api/*`, RCON protocol, auth tokens, Dynmap proxy, world inspection.
- Depends on: Python stdlib, local Paper files, RCON, optional `libcubiomes_shim.so`.
- Used by: `web-1.8/admin.js` and `web-1.12/admin.js`.

**Game layer:**
- Purpose: Run version-specific Paper and plugins.
- Location: `server-1.8/`, `server-1.12/`
- Contains: `server.jar`, properties, worlds, plugins, caches.
- Depends on: Java.
- Used by: Waterfall and admin bridge.

## Data Flow

### Primary Startup Path

1. Docker invokes `/usr/local/bin/eaglerx-start`, copied from `script/start_server.sh` (`Dockerfile`).
2. The script requires `MINECRAFT_VERSION`, validates `1.8` or `1.12`, and initializes a mounted application directory (`script/start_server.sh`).
3. It links `web/` and `server/` to the selected version trees, writes EULA/RCON properties, and optionally links legacy worlds.
4. It creates tmux session `mcserver`, starts `bungee/run.sh`, waits for port 5200, then starts the selected `server/run.sh`.
5. It starts `script/http_server.py`, monitors Bungee, Paper, and HTTP, and shuts all services down in order when a core process exits or the container receives `TERM`/`INT`.

### Client Request Path

1. Browser loads static client content through EaglercraftXBungee on port 5200 (`bungee/plugins/EaglercraftXBungee/listeners.yml`).
2. The WebSocket client reaches Waterfall, which routes the `lobby` server to `localhost:25565` (`bungee/config.yml`).
3. Paper handles gameplay and plugin behavior in the active `server/` alias.

### Admin Control Path

1. Admin UI detects `/api/status` and authenticates with `/api/login` on port 5201 (`web-1.12/admin.js`, `script/http_server.py`).
2. Authenticated calls use `/api/rcon`, `/api/config`, `/api/runtime-state`, `/api/world-state`, `/api/seed`, `/api/structures`, `/api/player-location`, or `/api/system`.
3. The bridge validates inputs, reads local state, sends RCON commands to `127.0.0.1:25575`, or restarts the Paper tmux pane.

**State Management:**
- Persistent state lives in the selected server tree or a full application bind mount; legacy world-only state can be linked from `server-data/`.
- The Python bridge keeps short-lived in-process caches for player markers and world state (`script/http_server.py`).
- Runtime selection is represented by the two `web` and `server` symlinks.

## Key Abstractions

**Active version aliases:**
- Purpose: Give Bungee, Paper scripts, and Python fixed paths while selecting version data at runtime.
- Examples: `script/start_server.sh`, `bungee/plugins/EaglercraftXBungee/listeners.yml`, `script/http_server.py`.
- Pattern: Replace safe empty directories or symlinks with `ln -sfnT` targets.

**HTTP Handler:**
- Purpose: Combine static file serving, admin API routing, and Dynmap proxying.
- Examples: `script/http_server.py:1172`.
- Pattern: Subclass `SimpleHTTPRequestHandler`; route by method/path; return JSON for API failures.

**RCON bridge:**
- Purpose: Translate authenticated HTTP actions into Paper console commands.
- Examples: `script/http_server.py:1086`, `script/http_server.py:1143`.
- Pattern: Pack/read Source RCON packets, retry transient connection failures, map errors to HTTP status.

## Entry Points

**Docker entrypoint:**
- Location: `Dockerfile`, `/usr/local/bin/eaglerx-start`
- Triggers: Container start.
- Responsibilities: Delegate to `script/start_server.sh`.

**Runtime shell entrypoint:**
- Location: `script/start_server.sh`
- Triggers: Docker or direct shell invocation.
- Responsibilities: Select version, configure persistence, start services in order, monitor them, and coordinate shutdown.

**Proxy process:**
- Location: `bungee/run.sh`
- Triggers: tmux pane 0.0.
- Responsibilities: Run `bungee/bungee.jar`.

**Paper process:**
- Location: `server-1.8/run.sh`, `server-1.12/run.sh`
- Triggers: tmux pane 0.1.
- Responsibilities: Run the selected `server.jar`.

**HTTP process:**
- Location: `script/http_server.py:1494`
- Triggers: Startup shell after tmux creation.
- Responsibilities: Listen on `0.0.0.0:5201`.

## Architectural Constraints

- **Threading:** The control plane uses stdlib `ThreadingHTTPServer`; locks serialize shared server-property writes, restarts, login-attempt state, and RCON timing (`script/http_server.py`).
- **Process order:** Bungee must start before Paper so the proxy route is ready (`script/start_server.sh`).
- **Port boundaries:** Public game/web traffic uses 5200; admin/fallback HTTP uses 5201; Paper and RCON bind to localhost ports 25565 and 25575.
- **Version coupling:** Each container selects one version pair; parallel versions require separate containers and persistent directories.
- **Global state:** Module-level environment/configuration, caches, and auth seed are defined in `script/http_server.py`.
- **Circular imports:** Not detected; the project is primarily shell/configuration plus standalone Python and Java artifacts.

## Anti-Patterns

### Legacy monolithic launcher

**What happens:** `main.sh` performs repository cloning, external downloads, client compilation, Waterfall updates, and runtime launch in one script.
**Why it's wrong:** Build, update, and runtime concerns share mutable working-directory state.
**Do this instead:** Use `Dockerfile` plus `script/start_server.sh` for the current runtime path; treat `main.sh` as a legacy build workflow.

### Direct public Paper exposure

**What happens:** The proxy route is configured for `localhost:25565`, while public Eagler traffic enters through port 5200.
**Why it's wrong:** Exposing Paper directly bypasses the intended proxy and client protocol boundary.
**Do this instead:** Publish port 5200 and keep Paper/RCON local as defined in `bungee/config.yml` and `script/http_server.py`.

## Error Handling

**Strategy:** Shell startup exits on fatal validation/configuration errors; the HTTP bridge returns JSON error responses and HTTP status codes; RCON retries transient failures.

**Patterns:**
- `set -e` plus explicit version/path checks in `script/start_server.sh`.
- API handlers return 400 for malformed input, 403 for failed auth, 500/503 for backend failures (`script/http_server.py`).
- `safe_link_dir` refuses to replace a populated real directory (`script/start_server.sh`).

## Cross-Cutting Concerns

**Logging:** Startup prefixes messages with `[start]`; HTTP access messages use `[http:5201]`; Java services log through Waterfall/Paper.
**Validation:** Managed server properties are allowlisted and normalized in `script/http_server.py`; structure searches clamp coordinates/radius/limits.
**Authentication:** RCON APIs are registered only when `RCON_PASSWORD` is set; login returns a signed expiring token derived from `ADMIN_AUTH_SECRET` or the RCON password.

---

*Architecture analysis: 2026-08-20*
