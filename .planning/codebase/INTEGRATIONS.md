# External Integrations

**Analysis Date:** 2026-08-20

## APIs & External Services

**Eaglercraft client gateway:**
- EaglercraftX browser clients connect to the EaglercraftXBungee listener at `bungee/plugins/EaglercraftXBungee/listeners.yml` (`0.0.0.0:5200`).
  - SDK/Client: `bungee/plugins/EaglerXBungee-1.3.6.jar`.
  - Auth: Built-in Eaglercraft authentication configured by `bungee/plugins/EaglercraftXBungee/authservice.yml`.
- The gateway serves `web/`, which is a runtime symlink to `web-1.8/` or `web-1.12/`.

**Dynmap:**
- `script/http_server.py` proxies `/dynmap/` to `DYNMAP_HOST:DYNMAP_PORT`, defaulting to `127.0.0.1:8123`.
  - SDK/Client: `server-1.8/plugins/Dynmap.jar` and `server-1.12/plugins/Dynmap.jar`.
  - Auth: No proxy-specific authentication detected.

**Legacy build downloads:**
- `main.sh` downloads the EaglercraftX source from GitHub, MCP from `modcoderpack.com`, the Minecraft 1.8.8 client and metadata from Mojang launcher endpoints, and Waterfall metadata/artifacts from PaperMC API.
  - SDK/Client: `git`, `wget`, `curl`, `jq` shell commands.
  - Auth: No credentials configured.

**Client certificate sources:**
- `bungee/plugins/EaglercraftXBungee/updates.yml` references `eaglercraft.com` and `deev.is` certificate URLs while update checks are disabled by the current settings.

## Data Storage

**Databases:**
- SQLite skin cache at `bungee/eaglercraft_skins_cache.db`.
  - Connection: `jdbc:sqlite:eaglercraft_skins_cache.db` in `bungee/plugins/EaglercraftXBungee/settings.yml`.
  - Client: Internal EaglercraftXBungee SQL driver with `bungee/plugins/EaglercraftXBungee/drivers/sqlite-jdbc.jar`.
- SQLite Eaglercraft authentication database at `bungee/eaglercraft_auths.db`.
  - Connection: `jdbc:sqlite:eaglercraft_auths.db` in `bungee/plugins/EaglercraftXBungee/authservice.yml`.
  - Client: Internal EaglercraftXBungee SQL driver.

**File Storage:**
- Local filesystem only: selected server data, worlds, plugins, logs, web assets, and configuration under `/eaglerX-1.8-server`.
- Docker startup copies the image payload from `/opt/eaglerX-1.8-server-image` into an empty mounted `APP_DIR`.
- Legacy optional world-only persistence uses `SERVER_DATA_DIR` and symlinks world directories into `server/`.

**Caching:**
- EaglercraftXBungee SQLite skin cache.
- In-process short-lived player/world caches in `script/http_server.py`.

## Authentication & Identity

**Auth Provider:**
- Built-in EaglercraftXBungee account system configured in `bungee/plugins/EaglercraftXBungee/authservice.yml`.
  - Implementation: SQLite-backed password registration/login through the `/eagler` command and login prompt.
- Administration API authentication uses `RCON_PASSWORD` for `/api/login`, then signed bearer tokens for management requests in `script/http_server.py`.
  - Secret: `ADMIN_AUTH_SECRET` optionally supplies the token signing seed; its default is derived from `RCON_PASSWORD`.
  - Controls: Tokens default to an eight-hour lifetime, and five failed logins from one source trigger a ten-minute lockout.

## Monitoring & Observability

**Error Tracking:**
- None detected.

**Logs:**
- Java proxy/server logs are written by Waterfall/Paper under runtime directories.
- Startup status and failures are emitted to stdout by `script/start_server.sh`.
- `script/http_server.py` prints service startup status and uses HTTP error responses for API failures.

## CI/CD & Deployment

**Hosting:**
- Docker images are published to `ghcr.io/yangchuansheng/eaglerx1.8server:<tag>` by the release workflow or `build.sh`.
- `.github/workflows/release.yml` validates tagged releases and publishes the tested image to GHCR.

**CI Pipeline:**
- Tagged releases and manual historical reruns execute the complete release gate before GHCR publication.

## Environment Configuration

**Required env vars:**
- `MINECRAFT_VERSION` - Required value `1.8` or `1.12`.

**Optional env vars:**
- `RCON_PASSWORD` - Enables RCON and the admin API.
- `APP_DIR`, `IMAGE_APP_DIR`, `SERVER_DATA_DIR` - Data/image locations.
- `DYNMAP_HOST`, `DYNMAP_PORT` - Dynmap target.
- `ADMIN_AUTH_SECRET`, `ADMIN_AUTH_TOKEN_TTL` - Admin token behavior.
- `TMUX_SESSION`, `TMUX_SERVER_PANE` - tmux targeting.
- `CUBIOMES_SHIM_PATH` - Native library path.
- `RCON_CONNECT_INTERVAL`, `RCON_SOCKET_TIMEOUT` - RCON connection tuning.

**Secrets location:**
- Supplied through runtime environment, primarily `RCON_PASSWORD` and optionally `ADMIN_AUTH_SECRET`; no secret manager integration detected.

## Webhooks & Callbacks

**Incoming:**
- HTTP requests to EaglercraftXBungee on port 5200.
- HTTP requests to the Python fallback/admin service on port 5201, including `/api/status`, `/api/login`, `/api/rcon`, `/api/config`, `/api/seed`, `/api/structures`, `/api/player-location`, `/api/runtime-state`, `/api/world-state`, `/api/system`, and `/dynmap/`.

**Outgoing:**
- RCON TCP requests from `script/http_server.py` to `127.0.0.1:25575`.
- Dynmap HTTP proxy requests from `script/http_server.py` to `DYNMAP_HOST:DYNMAP_PORT`.
- Optional external STUN/TURN connections configured in `bungee/plugins/EaglercraftXBungee/ice_servers.yml`.
- Optional certificate/update HTTP downloads configured in `bungee/plugins/EaglercraftXBungee/updates.yml`.

---

*Integration audit: 2026-08-20*
