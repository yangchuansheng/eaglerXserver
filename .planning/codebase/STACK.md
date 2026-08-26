# Technology Stack

**Analysis Date:** 2026-08-20

## Languages

**Primary:**
- Java - Prebuilt Paper Minecraft servers in `server-1.8/server.jar` and `server-1.12/server.jar`, plus Waterfall in `bungee/bungee.jar` and Bukkit plugins.
- JavaScript - Browser clients and administration UI in `web-1.8/*.js` and `web-1.12/*.js`.

**Secondary:**
- Python 3 - Embedded HTTP server, RCON bridge, Dynmap proxy, and world/structure administration in `script/http_server.py`.
- Bash - Container startup, process orchestration, build/publish, and legacy setup scripts in `script/start_server.sh`, `build.sh`, and `main.sh`.
- C - Cubiomes FFI adapter in `script/cubiomes_shim.c`, compiled as `script/libcubiomes_shim.so`.
- YAML/JSON/properties - Runtime configuration in `bungee/`, `server-1.8/`, `server-1.12/`, and `web-*`.

## Runtime

**Environment:**
- Java runtime supplied by the base image `registry.cn-hangzhou.aliyuncs.com/chenxuan/java:0.0.1`; the repository targets Java-based Paper/Waterfall processes.
- Python 3 standard library for `script/http_server.py`.
- Linux container with Bash, `tmux`, shared libraries, and filesystem symlink support.

**Package Manager:**
- No application package manager or dependency manifest detected.
- Lockfile: missing.
- Java dependencies are committed as JAR artifacts under `server-*`, `bungee/`, and `misc/`.

## Frameworks

**Core:**
- Paper 1.8.8 - Minecraft server in `server-1.8/server.jar`.
- Paper 1.12.2 - Minecraft server in `server-1.12/server.jar`.
- Waterfall/BungeeCord - Proxy process in `bungee/bungee.jar`.
- EaglercraftXBungee - WebSocket gateway and static web server in `bungee/plugins/EaglercraftXBungee/`.
- Python `http.server` - Administration API, static fallback, and proxy in `script/http_server.py`.

**Testing:**
- Python standard-library `unittest` regression suite in `tests/test_regressions.py`.

**Build/Dev:**
- Docker - Image packaging in `Dockerfile`.
- `tmux` - Runs proxy, selected Paper server, and HTTP service in one container via `script/start_server.sh`.
- `ffmpeg`, Java 11, Maven Central, MCP 9.18, and Mojang 1.8.8 artifacts - Legacy client rebuild flow in `main.sh` and `buildconf*.json`.

## Key Dependencies

**Critical:**
- `server-1.8/server.jar` - Paper 1.8.8 runtime.
- `server-1.12/server.jar` - Paper 1.12.2 runtime.
- `bungee/bungee.jar` - Waterfall proxy runtime.
- `bungee/plugins/EaglerXBungee-1.3.6.jar` - Eaglercraft WebSocket/HTTP gateway.
- `script/http_server.py` - Port 5201 API and RCON integration.
- `script/libcubiomes_shim.so` - Native seed, spawn, and structure calculations loaded through `ctypes`.

**Infrastructure:**
- `server-*/plugins/Dynmap.jar` - Minecraft map rendering.
- `server-*/plugins/LoginSecurity-3.2.0-Bukkit.jar` - Server-side login plugin.
- `server-*/plugins/WorldEdit/config.yml` and `worldedit-bukkit-6.1.jar` - World editing.
- `server-*/plugins/SimpleHomes.jar` and `SimpleTpa.jar` - Gameplay utilities.
- `bungee/plugins/EaglercraftXBungee/drivers/sqlite-jdbc.jar` - SQLite JDBC driver used by Eaglercraft gateway databases.
- `misc/Carbon.jar`, `misc/Carbon-ProtocolLib.jar`, and `misc/npaper-1.7.jar` - Legacy alternative server assets referenced by `selsrv.sh`.

## Configuration

**Environment:**
- `MINECRAFT_VERSION` is required and accepts `1.8` or `1.12`; `script/start_server.sh` selects `server-*` and `web-*` through runtime symlinks.
- `RCON_PASSWORD` is optional; when set, startup enables RCON and `script/http_server.py` registers management endpoints.
- `APP_DIR`, `IMAGE_APP_DIR`, and `SERVER_DATA_DIR` control image data initialization and legacy world persistence.
- `DYNMAP_HOST`, `DYNMAP_PORT`, `ADMIN_AUTH_SECRET`, `ADMIN_AUTH_TOKEN_TTL`, `TMUX_SESSION`, `TMUX_SERVER_PANE`, `CUBIOMES_SHIM_PATH`, `RCON_CONNECT_INTERVAL`, and `RCON_SOCKET_TIMEOUT` tune the Python service.
- Static server/plugin settings live in `server-1.8/server.properties`, `server-1.12/server.properties`, `bungee/config.yml`, and `bungee/plugins/EaglercraftXBungee/*.yml`.

**Build:**
- `Dockerfile` copies the complete repository into `/opt/eaglerX-1.8-server-image`, installs the startup entrypoint, and exposes runtime defaults through `ENV`.
- `build.sh` builds `ghcr.io/yangchuansheng/eaglerx1.8server:<tag>` and optionally pushes it.
- `buildconf.json` and `buildconf_template.json` configure the legacy Eaglercraft client compiler.
- `replit.nix` declares development tools including JRE 8, JDK 11, Git, tmux, wget, curl, jq, ffmpeg, and dialog.

## Platform Requirements

**Development:**
- Linux-like shell, Docker for image builds, Java, Python 3, Bash, and `tmux` for the current startup flow.
- Native Cubiomes library must be loadable at `CUBIOMES_SHIM_PATH` for seed/structure features.

**Production:**
- Linux Docker host running the image with `MINECRAFT_VERSION` set.
- Externally reachable port 5200 for Eaglercraft WebSocket plus HTTP; port 5201 serves the fallback/admin API when published.
- Persistent writable mount at `/eaglerX-1.8-server` is supported and preferred by `script/start_server.sh`.

---

*Stack analysis: 2026-08-20*
