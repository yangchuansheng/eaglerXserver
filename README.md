# EaglercraftX Server

Run a Minecraft server that players can join from their browser, with persistent storage and an admin panel for managing players, worlds, and plugins. The Docker image includes EaglercraftX 1.8 / 1.12 clients and Paper 1.8.8 / 1.12.2 servers; choose the game version at startup.

![EaglercraftX admin panel](./docs/images/admin-panel.png)

<!-- README-I18N:START -->

**English** | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md) | [Español](./README.es.md) | [Français](./README.fr.md) | [Deutsch](./README.de.md) | [Português (Brasil)](./README.pt-BR.md) | [Русский](./README.ru.md) | [العربية](./README.ar.md) | [हिन्दी](./README.hi.md) | [Bahasa Indonesia](./README.id.md) | [Türkçe](./README.tr.md)

<!-- README-I18N:END -->

[Quick start](#quick-start) · [Joining the server](#joining-the-server) · [Admin panel and plugins](#admin-panel-and-plugins) · [Backups and upgrades](#backups-upgrades-and-rollbacks) · [Troubleshooting](#operations-and-troubleshooting) · [Environment variables](#environment-variables) · [Admin API](#admin-api) · [Development and releases](#development-builds-and-releases) · [Reporting issues](#reporting-issues)

## Features

| Feature | Details |
|------|------|
| Server management | Paper readiness, online players, ticks per second (TPS), weather, time, game rules, configuration, and controlled restarts |
| Players and worlds | Operator status (OP), whitelists, kicks, bans, teleportation, item commands, world saves, and world borders |
| Plugin management | Separate repositories for each game version; upload, enable, disable, and delete plugins, with changes applied after a Paper restart |
| Maps and seeds | Embedded Dynmap, player locations, native structure lookup, and links to an external Seed Map |
| Bundled plugins | LoginSecurity, SimpleHomes, SimpleTpa, WorldEdit, Dynmap |

## Quick start

### 1. Prepare the host

- **Host**: Install Docker and provision persistent storage. The examples use Linux paths. Published images target AMD64; ARM64 emulation and native library compatibility require separate validation. See the [architecture decision](docs/adr/0006-publish-linux-amd64-only.md).
- **Memory**: Paper and Bungee each use `-Xms256M -Xmx256M`. Allow additional memory for the JVM outside its heap, world generation, and plugins. To adjust heap sizes, edit `run.sh` in the corresponding runtime directory.
- **EULA**: The startup script writes `eula=true`. Read and accept the [Minecraft EULA](https://www.minecraft.net/en-us/eula) before deploying.

### 2. Start Paper 1.12.2

Run the following commands on the server. Replace `YOUR_SERVER` with an IP address or domain that players can reach, and replace `replace-with-a-strong-password` with your admin password.

This example mounts `/data/eagler-1.12` on the host at `/eaglerX-1.8-server` inside the container, persisting the **entire runtime directory**: worlds, plugins, configuration, and frontend files. An empty directory is initialized automatically on first use. If an existing directory is incomplete, startup preserves its contents and exits. For an existing deployment, follow [Backups, upgrades, and rollbacks](#backups-upgrades-and-rollbacks) to migrate the runtime files.

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5

docker run -d \
  --name eaglerx-1.12 \
  --platform linux/amd64 \
  --stop-timeout 45 \
  -p 5200:5200 \
  -p 127.0.0.1:5201:5201 \
  -v /data/eagler-1.12:/eaglerX-1.8-server \
  -e MINECRAFT_VERSION=1.12 \
  -e 'RCON_PASSWORD=replace-with-a-strong-password' \
  -e 'PUBLIC_GAME_URL=http://YOUR_SERVER:5200' \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
```

### 3. Open the admin panel and check readiness

| Entry point | Address | How to use it |
|------|------|----------|
| Game | `http://YOUR_SERVER:5200/` | Share this with players and follow the [joining instructions](#joining-the-server) |
| Admin panel | `http://127.0.0.1:5201/admin` | Open from the host and sign in with the admin password set at startup |

Initial world generation can take a few minutes. Startup is complete when the admin panel shows **Paper is ready**. For a prolonged wait or an error, see [Operations and troubleshooting](#operations-and-troubleshooting).

### Remote management and ports

To manage a remote server, open an SSH tunnel from your own computer. Replace `user@YOUR_SERVER` with the server's SSH login address:

```bash
ssh -N -L 5201:127.0.0.1:5201 user@YOUR_SERVER
```

Keep the tunnel open, then visit `http://127.0.0.1:5201/admin`. You can also use an HTTPS reverse proxy with the host's `127.0.0.1:5201` as its upstream. A VPN management endpoint must be able to forward traffic to that loopback address.

| Port | Purpose | Exposure |
|------|------|----------|
| 5200 | HTTP game page, public static files, and WebSocket game connections | Expose to players |
| 5201 | Admin panel, HTTP fallback, and Dynmap proxy | Bind to `127.0.0.1` on the host |
| 25565 | Paper | Localhost inside the container |
| 25575 | RCON | Localhost inside the container |

### Custom domains, HTTPS, and the game URL

Set `PUBLIC_GAME_URL` to **the HTTP(S) game URL players actually use**. The admin panel uses it to generate quick-join links and `ws` / `wss` addresses. When left empty, it derives an HTTP URL from the admin panel's current hostname on port 5200 (`http://主机名:5200/`). Set it explicitly when using an SSH tunnel, a separate admin domain, or a custom game port.

An HTTPS game endpoint requires DNS, a certificate, and HTTP and WebSocket forwarding to **5200**. Point the admin proxy at **5201**. `PUBLIC_GAME_URL` is used only to generate connection addresses; configure the proxy and certificate in your deployment.

### Choosing 1.8 or running both versions

`2.2.5` is the image release version. `MINECRAFT_VERSION=1.8` selects Paper 1.8.8, and `1.12` selects Paper 1.12.2. Each container runs one game version at a time and uses its own runtime directory.

To run 1.8, adjust these parameters in the quick-start command:

| Parameter | Run 1.8 on its own | Run 1.8 alongside 1.12 |
|------|-------------|---------------------|
| Container name | `--name eaglerx-1.8` | Same as left |
| Game version | `-e MINECRAFT_VERSION=1.8` | Same as left |
| Full runtime mount | `-v /data/eagler-1.8:/eaglerX-1.8-server` | Same as left |
| Game port | `-p 5200:5200` | `-p 5300:5200` |
| Admin port | `-p 127.0.0.1:5201:5201` | `-p 127.0.0.1:5301:5201` |
| Public game URL | `http://YOUR_SERVER:5200` | `http://YOUR_SERVER:5300` |

Set `PUBLIC_GAME_URL` to the URL for that instance. To manage the second instance remotely, use `ssh -N -L 5301:127.0.0.1:5301 user@YOUR_SERVER` and open `http://127.0.0.1:5301/admin`.

## Joining the server

1. Open the game URL, or use the quick-join link your server owner shares from the admin panel's Overview page. The 1.12 client starts with an empty server list; add `ws://YOUR_SERVER:5200/` in Multiplayer, or use the corresponding `wss://` address for an HTTPS game endpoint.
2. On your first visit, follow the LoginSecurity prompt and enter `/register <password>`. Use `/login <password>` on later visits. Registration is required by default, passwords must contain at least 6 characters, and the login timeout is 30 seconds.
3. LoginSecurity manages player account passwords. The admin panel uses the server owner's `RCON_PASSWORD`.

SimpleHomes provides `/sethome <name>`, `/home <name>`, and `/homes`. SimpleTpa provides `/tpa <player>`, `/tpaccept`, and `/tpdeny`. Permissions and behavior depend on the current plugin configuration.

## Admin panel and plugins

### Signing in and applying changes

Setting `RCON_PASSWORD` enables RCON and the admin API. After login, the browser keeps an admin token in the current session; tokens expire after 8 hours by default. Logging out clears the local token. The interface defaults to English, supports Simplified Chinese, and remembers your language choice for the current site.

You can sign in while Paper is starting. Game controls become available when Paper is ready.

| Action | When it takes effect |
|------|----------|
| Weather, time, game rules, player commands, and whitelist commands | Sent to the running Paper instance; check the console response |
| Server configuration, including MOTD, player limit, view distance, and PVP | Written to `server.properties` and applied after a Paper restart |
| Plugin uploads, enabling, disabling, and deletion | Saved to the plugin repository and applied after a Paper restart |
| The admin panel's Minecraft restart action | Performs a controlled Paper restart while Bungee and the admin panel keep running |
| Shutdown from the admin panel, or `stop` in the console | Paper exits, triggering shutdown of the entire container |

Dynmap is available through the admin panel's `/dynmap/` proxy. Native structure lookup uses the cubiomes component bundled in the image. Structures and approximate spawn locations are calculated from the world seed; player locations come from Dynmap or player save data. Opening the external Seed Map includes the world seed in the destination URL.

### Plugin repositories and data

The active version's repository is at `server-data/plugins-1.8` or `server-data/plugins-1.12`. The `enabled/` directory contains enabled plugin packages and plugin data; `disabled/` contains disabled packages. Paper's `plugins` path points to the active repository's `enabled/` directory.

The first startup imports bundled plugin packages and data. Later startups preserve the repository's current state, including manual edits, disabled packages, and deletions. Mounting the full runtime directory persists all of this data.

The admin panel shows the active game version, plugin file sizes, modification times, state at the next startup, and whether a restart is pending:

- Uploads must be JAR files containing `plugin.yml` at the archive root. Filenames must end in lowercase `.jar`, and the size limit is **64 MiB**. Duplicate filenames return a conflict.
- After uploading, enabling, disabling, or deleting a plugin, use the admin panel's restart action to load the updated set. Loaded code stays active until Paper stops.
- Deleting a plugin removes its JAR and retains its configuration and databases. Reinstalling a compatible plugin that uses the same data directory can reuse that data.
- JARs execute with the Paper process's permissions. Use trusted sources, review and scan packages before installation, and take a backup.

<details>
<summary>Existing worlds and a separate data directory (legacy support)</summary>

`PERSISTENT_DATA_ROOT` sets a shared root for plugin repositories and legacy world mounts. `SERVER_DATA_DIR` is its compatibility alias. Mounting the full runtime directory is the default deployment method.

**An empty separate data directory initializes only the plugin repository.** World symlinks require the corresponding worlds to exist in that data root. Newly generated worlds stay in the version-specific `server-版本/` directory and are persisted by the full runtime mount.

To migrate existing worlds, stop the server and take a backup, then prepare the `<level-name>`, `<level-name>_nether`, and `<level-name>_the_end` directories. Their default names are `world`, `world_nether`, and `world_the_end`. The entrypoint can fall back to these defaults and preserves any real world directories already at the server paths. Use a separate data root for each version, then check each world symlink's actual target after startup.

</details>

## Backups, upgrades, and rollbacks

### Stop the server and back up

These commands use the container and mount from the quick start. Backups contain worlds, player state, plugin data, configuration, authentication databases, and the admin password. Store them in a directory with restricted access.

```bash
docker stop -t 45 eaglerx-1.12
sudo install -d -m 700 /data/backups
sudo tar -czf "/data/backups/eagler-1.12-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /data eagler-1.12
```

For a routine backup, run `docker start eaglerx-1.12` when finished. During an upgrade, keep the old container stopped. If you use an external `PERSISTENT_DATA_ROOT`, back up that root as well; tar preserves symlinks themselves by default.

When the entrypoint receives a stop signal, it gives Paper up to 30 seconds to exit, followed by up to 10 seconds for Bungee. The example's 45-second Docker stop timeout allows time for this sequence. See [Docker's stop behavior](https://docs.docker.com/reference/cli/docker/container/stop/).

### Prepare the upgrade in a new directory

**The full runtime directory is initialized from the image only on first startup.** After changing images, the existing mount continues to supply the server, frontend, and Python backend files. An upgrade requires explicitly updating the runtime files and migrating persistent state.

**Step 1: Stop the server and back up.** Keep the old container, runtime directory, and image version.

**Step 2: Prepare a new runtime directory.** Copy the complete template from the target image. This example targets `2.2.5`; choose an unused template container name and directory:

```bash
docker pull --platform linux/amd64 ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
docker create --name eaglerx-upgrade-template --platform linux/amd64 \
  ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5
sudo mkdir /data/eagler-1.12-next
sudo docker cp eaglerx-upgrade-template:/opt/eaglerX-1.8-server-image/. \
  /data/eagler-1.12-next/
docker rm eaglerx-upgrade-template
```

Leave the template container unstarted. [docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) supports copying files from stopped containers. After copying the template, migrate persistent state from the old directory:

| Data | How to migrate it |
|------|----------|
| `server-1.12/<level-name>` and its Nether and End directories | Copy the complete worlds and keep `level-name` consistent with the directory names |
| `server-data/` | Copy the entire plugin repository, marker files, and legacy world directories |
| Paper's `*.properties`, `*.yml`, and `*.json` files | Merge configuration against the new template; preserve operators, whitelists, bans, and player caches |
| Bungee configuration, authentication databases, and skin caches | Migrate configuration and databases individually; check for custom state in the root and plugin directories |
| Custom frontend files, plugins, and launch options | Merge customizations as needed; use server JARs, scripts, and admin assets from the target image |

The entrypoint recreates the `server/`, `web/`, and Paper `plugins` symlinks. Copy any external data directory to a new host directory, then mount it in the new container at its original container path. Keep the old data root for the old container. Include state from other versions and custom worlds in your migration checklist.

**Step 3: Start the new container.** Use the [quick-start command](#2-start-paper-1122), changing the container name to `eaglerx-1.12-next`, the host directory to `/data/eagler-1.12-next`, and the image to your target version. Keep the original game version, password, public URL, and port mappings.

**Step 4: Verify the migration.** Confirm that Paper is ready, players can join, existing worlds are intact, plugins load, and whitelists and maps work as expected. Once verified, set a retention period for the old container, image, and backups.

### Rollback and recovery

With the old container and directory retained, stop the new container and start the old one:

```bash
docker stop -t 45 eaglerx-1.12-next
docker start eaglerx-1.12
```

A rollback restores the state saved in the old directory. Preserve data created while the new container was running so it remains available for recovery. To restore a compressed backup, extract it into a new directory, mount the extracted `eagler-1.12` directory as the full runtime directory, and use the image version and launch options associated with that backup.

## Operations and troubleshooting

These commands use the default container name:

```bash
# Container health and entrypoint / HTTP logs
docker inspect --format '{{.State.Status}} / {{.State.Health.Status}}' eaglerx-1.12
docker logs --tail 100 eaglerx-1.12

# Paper console output in the managed tmux session
docker exec -e TMUX_TMPDIR=/tmp/eaglerx-tmux eaglerx-1.12 \
  tmux capture-pane -p -t mcserver:0.1 -S -100

# Public status probe when RCON is enabled, via the host or SSH tunnel
curl -sS http://127.0.0.1:5201/api/status
```

Paper and Bungee run in tmux. The Paper console above uses the default pane `mcserver:0.1`; Bungee uses `mcserver:0.0`. Docker's health check probes ports 5200, 5201, and 25565. The admin panel also probes RCON to determine Paper readiness.

| Symptom | What to check |
|------|------------|
| The container exits immediately | Verify that `MINECRAFT_VERSION` is `1.8` or `1.12`, then check the logs for the specific error |
| Startup reports an incomplete runtime directory | Initialize an empty directory or restore a complete backup; retain the current directory for investigation |
| The admin panel opens while Paper is still starting | Check the Paper console for world generation and plugin loading progress; the panel updates automatically when Paper is ready |
| The remote admin panel is unreachable | Check that the SSH tunnel or admin proxy can reach `127.0.0.1:5201` on the host |
| The quick-join address is wrong or connections fail over HTTPS | Check `PUBLIC_GAME_URL`, the public port, and WebSocket forwarding on the game proxy |
| `/api/status` returns 404 | Set `RCON_PASSWORD` and recreate the container; the startup script uses it to enable RCON |
| Login returns 429 | Five failed attempts from one source within the failure window trigger a 10-minute lockout; administrators behind a tunnel or proxy may share a source |
| Configuration or plugin changes are saved, but the old behavior persists | Use the admin panel's controlled Paper restart, then check the running state |
| Dynmap returns 502 | Check that Dynmap is enabled and has finished loading, then check its HTTP listen address and port |
| Native structure lookup fails | Check the `linux/amd64` runtime environment, native library loading errors, and world seed retrieval |

The entrypoint starts Bungee, Paper, and HTTP in that order and monitors them continuously. If any core service exits, it shuts down the whole container and returns a failure status. It performs an orderly shutdown on `SIGTERM` / `SIGINT`. Configure the restart policy for your deployment, accounting for the container exit triggered by an admin-panel shutdown.

## Environment variables

Pass these with `docker run -e`. To change a container's environment variables, recreate it using the existing mount.

| Variable | Default | Description |
|------|--------|------|
| `MINECRAFT_VERSION` | Required | `1.8` selects Paper 1.8.8; `1.12` selects Paper 1.12.2 |
| `RCON_PASSWORD` | Empty | Enables RCON and the admin API when set; authenticated admin endpoints are disabled when empty |
| `PUBLIC_GAME_URL` | Empty | The public HTTP(S) game URL used to generate quick-join links and WebSocket addresses |
| `PERSISTENT_DATA_ROOT` | `${APP_DIR}/server-data` | Root for plugin repositories and legacy mounts of existing worlds; an empty directory initializes the plugin repository automatically |
| `SERVER_DATA_DIR` | Empty | Compatibility alias for `PERSISTENT_DATA_ROOT`; an explicit value for the latter takes precedence |
| `ADMIN_AUTH_TOKEN_TTL` | `28800` | Admin token lifetime in seconds |
| `ADMIN_AUTH_SECRET` | Derived from the RCON password | Optional token-signing secret |
| `DYNMAP_HOST` / `DYNMAP_PORT` | `127.0.0.1` / `8123` | Dynmap upstream address used by the admin backend |

## Admin API

For script integrations. All endpoints use admin port **5201**. The admin panel covers day-to-day operations.

<details>
<summary>Endpoints, authentication, and curl examples</summary>

“Public” describes the endpoint's own authentication requirements. Access the admin port through an [SSH tunnel or admin proxy](#remote-management-and-ports).

| Endpoint | Access requirements |
|------|----------|
| `GET /api/connection-info` | Always available; returns the public game endpoint configuration |
| `GET /api/status` | Available when RCON is enabled; returns Paper status and related information |
| `POST /api/login` | Exchanges the admin password for a token when RCON is enabled |
| JSON admin endpoints such as `POST /api/rcon`, `/api/config`, `/api/system`, and `/api/plugins` | Request body must include a valid `token` |
| `POST /api/plugins/upload` | `Authorization: Bearer <token>`, a raw JAR request body, and the `X-Plugin-Filename` header |
| `GET /dynmap/` | Proxies directly to Dynmap; access is protected by the management connection |

JSON admin requests have a 64 KiB body limit and a 10-second read timeout. Raw plugin JAR uploads have a 64 MiB limit and a 30-second total read deadline. Administrators sharing a tunnel or reverse proxy source may share the same login lockout window.

```bash
# Exchange the management password for a token
curl -sS http://127.0.0.1:5201/api/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"replace-with-a-strong-password"}'

# Use the returned token for a management command
curl -sS http://127.0.0.1:5201/api/rcon \
  -H 'Content-Type: application/json' \
  -d '{"command":"list","token":"TOKEN_FROM_LOGIN"}'
```

</details>

## Development, builds, and releases

### Local changes and validation

Run these commands from the repository root with Python 3 and Docker installed. Edit admin assets in `web-1.8/`, then run the sync script to update `web-1.12/`. See the [runtime base-image decision](docs/adr/0007-retain-the-verified-runtime-base.md) for the base image and native library requirements.

```bash
python3 script/sync_admin_assets.py
python3 script/sync_admin_assets.py --check
docker build --platform linux/amd64 -t eaglerx-local:dev .
```

The local release gate also requires Node.js, tmux, `agent-browser`, and a working Chrome installation. CI pins `agent-browser@0.26.0`; see the [release workflow](.github/workflows/release.yml) for installation steps.

```bash
agent-browser doctor
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

Local checks cover Python syntax, server and plugin regressions, resources for both versions, admin assets, and browser flows in English and Simplified Chinese. Browser checks use a local Mock Admin API. Full release validation also builds the image and runs both Paper versions:

```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate
```

The gate sets `release_ready` to `true` in `summary.json` only after the full `--live` checks pass. See the [release gate documentation](docs/release-gate.md) for check coverage, evidence formats, and Linux temporary-mount permissions.

### Publishing a release

Official releases use `vMAJOR.MINOR` or `vMAJOR.MINOR.PATCH` Git tags. The workflow runs the full gate against a single image, then publishes that image to GHCR with version and commit SHA tags and a build provenance attestation. Automatic releases of the highest version update `latest`. Manual reruns update only the specified version and SHA tags.

```bash
gh workflow run release.yml -f release_tag=v2.2.5
```

`build.sh` wraps local builds; its `push` argument pushes the image directly. Official distribution follows the [full live gate requirement](docs/adr/0005-require-the-live-release-gate.md) and the tag workflow above.

## Reporting issues

Report deployment problems and feature requests through [GitHub Issues](https://github.com/yangchuansheng/eaglerXserver/issues). Include the image tag, `MINECRAFT_VERSION`, host architecture, redacted launch options, reproduction steps, and relevant error logs. Remove passwords and tokens before submitting.

## Credits

- Eaglercraft / EaglercraftX: lax1dude (Calder Young)
- Eaglercraft server: ayunami2000
- [Upstream](https://github.com/burgerhugger/ALL-server)
