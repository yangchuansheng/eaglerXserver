# Codebase Structure

**Analysis Date:** 2026-08-19

## Directory Layout

```text
eaglerXserver/
├── Dockerfile                         # Image packaging and entrypoint
├── build.sh                           # Image build/push wrapper
├── script/                            # Runtime launcher, HTTP bridge, native shim
├── bungee/                            # Waterfall proxy, modules, Eagler plugin config
├── server-1.8/                        # Paper 1.8.8 runtime tree
├── server-1.12/                       # Paper 1.12.2 runtime tree
├── web-1.8/                           # EaglercraftX 1.8 client and admin UI
├── web-1.12/                          # EaglercraftX 1.12 client and admin UI
├── misc/                              # Optional server/plugin binaries
├── main.sh                            # Legacy build/update/launch workflow
├── selsrv.sh                           # Legacy server software selector
└── .planning/codebase/                # Generated architecture map documents
```

## Directory Purposes

**`script/`:**
- Purpose: Own runtime orchestration and the control-plane implementation.
- Contains: `start_server.sh`, `http_server.py`, C shim source, compiled native library.
- Key files: `script/start_server.sh`, `script/http_server.py`, `script/cubiomes_shim.c`.

**`bungee/`:**
- Purpose: Own the public proxy and Eaglercraft gateway.
- Contains: Waterfall jar, plugin jars/configuration, listener and HTTP-root settings, optional command modules.
- Key files: `bungee/config.yml`, `bungee/run.sh`, `bungee/plugins/EaglercraftXBungee/listeners.yml`.

**`server-1.8/` and `server-1.12/`:**
- Purpose: Store version-specific Paper runtime assets and mutable game state.
- Contains: `server.jar`, `server.properties`, `spigot.yml`, plugin jars/configuration, caches, worlds/logs at runtime.
- Key files: `server-1.8/run.sh`, `server-1.12/run.sh`, each version's `server.properties`.

**`web-1.8/` and `web-1.12/`:**
- Purpose: Store version-specific Eaglercraft client payloads and the shared-shape admin UI.
- Contains: HTML launchers, compiled `classes.js`, assets, locale files, `admin.html`, `admin.css`, `admin.js`.
- Key files: `web-1.8/index.html`, `web-1.8/admin.html`, `web-1.8/admin.js`; corresponding `web-1.12` files.

**`misc/`:**
- Purpose: Hold optional legacy server/plugin binaries used by `selsrv.sh`.
- Contains: Carbon, ProtocolLib, and npaper jars.
- Key files: `misc/Carbon.jar`, `misc/Carbon-ProtocolLib.jar`, `misc/npaper-1.7.jar`.

**`.planning/codebase/`:**
- Purpose: Store generated mapper reference documents.
- Contains: Architecture, structure, technology, quality, and concerns documents created by GSD mappers.
- Key files: `ARCHITECTURE.md`, `STRUCTURE.md`.

## Key File Locations

**Entry Points:**
- `Dockerfile`: container entrypoint wiring.
- `script/start_server.sh`: current runtime launcher.
- `bungee/run.sh`: Waterfall process command.
- `server-1.8/run.sh`, `server-1.12/run.sh`: Paper process commands.
- `script/http_server.py`: port 5201 HTTP/API process.

**Configuration:**
- `Dockerfile`: image paths and environment defaults.
- `bungee/config.yml`: Waterfall listener/backend and proxy behavior.
- `bungee/plugins/EaglercraftXBungee/listeners.yml`: Eagler listener, static root, rate limits.
- `server-1.8/server.properties`, `server-1.12/server.properties`: Paper settings.
- `bungee/plugins/EaglercraftXBungee/settings.yml`: gateway plugin settings.

**Core Logic:**
- `script/start_server.sh`: version selection, persistence setup, process orchestration.
- `script/http_server.py`: admin API, RCON, state inspection, Dynmap and seed services.
- `web-1.8/admin.js`, `web-1.12/admin.js`: admin dashboard behavior.

**Testing:**
- Dedicated test directories and test files: Not detected.
- Runtime verification surfaces: `script/http_server.py` API endpoints and the Docker startup path.

## Naming Conventions

**Files:**
- Shell launchers use `*.sh` and descriptive lowercase names such as `start_server.sh`.
- Versioned resource trees use `server-<version>` and `web-<version>`.
- Runtime configuration uses the upstream format and names: `config.yml`, `settings.yml`, `server.properties`.

**Directories:**
- Top-level service/resource directories use lowercase names.
- Version directories encode the supported protocol/server version with a hyphen: `server-1.8`, `web-1.12`.
- Plugin directories follow upstream plugin names, such as `bungee/plugins/EaglercraftXBungee`.

## Where to Add New Code

**New Feature:**
- Runtime orchestration: `script/start_server.sh`.
- Admin/backend capability: `script/http_server.py`, adding a focused handler/helper alongside the existing route family.
- Admin UI capability: both `web-1.8/admin.js` and `web-1.12/admin.js`, keeping the interfaces aligned.
- Server behavior: version-specific plugin/configuration under `server-1.8/` or `server-1.12/`.

**New Component/Module:**
- Proxy/plugin configuration: `bungee/plugins/` and its related `bungee/*.yml` files.
- Optional native calculation: `script/` for source and the build artifact expected by `CUBIOMES_SHIM_PATH`.
- Optional legacy binaries: `misc/`, only when consumed by an existing selector workflow.

**Utilities:**
- Shared runtime helpers: `script/http_server.py` for HTTP/game-state concerns; shell helpers belong in `script/start_server.sh` when they are startup-specific.

## Placement and Runtime Conventions

- Keep version-specific assets in paired `server-<version>` and `web-<version>` directories.
- Resolve active resources through `server/` and `web/` aliases; `script/start_server.sh` owns alias creation.
- Keep public Eagler traffic on the proxy listener at 5200 and admin/fallback traffic on the Python bridge at 5201.
- Keep Paper-facing configuration inside the selected server tree; the bridge resolves it through the active `server/` alias.
- Preserve full-directory mount compatibility at `/eaglerX-1.8-server`; use separate host directories for simultaneous versions.

## Special Directories

**`server/` and `web/`:**
- Purpose: Active runtime aliases to the selected version trees.
- Generated: Yes, at startup by `script/start_server.sh`.
- Committed: No; ignored by `.gitignore`.

**`server-data/`:**
- Purpose: Optional legacy world-only persistence source.
- Generated: Runtime/user-managed.
- Committed: No; ignored by `.gitignore`.

**`server-*/cache/`:**
- Purpose: Paper patching/Mojang cache artifacts.
- Generated: Partly by Paper tooling and distribution contents.
- Committed: Present in the repository's version trees.

**`bungee/plugins/EaglercraftXBungee/drivers/`:**
- Purpose: Plugin JDBC driver storage.
- Generated: Distribution artifact.
- Committed: Present in the repository.

---

*Structure analysis: 2026-08-19*
