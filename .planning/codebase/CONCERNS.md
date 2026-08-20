# Codebase Concerns

**Analysis Date:** 2026-08-20

## Tech Debt

**Duplicated 1.8/1.12 runtime trees:**
- Issue: `server-1.8/` and `server-1.12/` duplicate plugins and configuration, while `web-1.8/` and `web-1.12/` duplicate `admin.html`, `admin.js`, and `admin.css`.
- Files: `server-1.8/`, `server-1.12/`, `web-1.8/admin.*`, `web-1.12/admin.*`, `script/start_server.sh`
- Impact: A security or behavior fix can land in one version and silently miss the other.
- Fix approach: Keep shared admin assets in one source location and add a build/copy verification; compare paired configuration files in CI.

**Two overlapping launch paths:**
- Issue: The current Docker path uses `script/start_server.sh`, while legacy `main.sh` performs network downloads, destructive cleanup, and a separate tmux layout.
- Files: `script/start_server.sh`, `main.sh`, `Dockerfile`, `README.md`
- Impact: Operators can follow documentation or scripts that produce materially different deployments.
- Fix approach: Retire the legacy path or clearly isolate it from the supported Docker entrypoint and test only the supported path.

**Mutable runtime files inside the image/application tree:**
- Issue: Startup rewrites `server.properties`, `eula.txt`, symlinks, worlds, logs, plugin state, and the skin cache in-place.
- Files: `script/start_server.sh`, `server-1.8/server.properties`, `server-1.12/server.properties`, `bungee/eaglercraft_skins_cache.db`
- Impact: Bind mounts and concurrent version containers can preserve stale configuration or make rollback difficult.
- Fix approach: Separate immutable distribution assets from an explicit data directory and create versioned backups before config migration.

## Known Bugs

**RCON is exposed through an unauthenticated-looking public HTTP surface:**
- Symptoms: Port 5201 binds to `0.0.0.0`; API authentication relies on a password/token sent by the browser.
- Files: `script/http_server.py:108-112`, `script/http_server.py:1499`, `README.md:76-113`
- Trigger: Publish port 5201 and configure `RCON_PASSWORD`.
- Workaround: Bind 5201 to a private interface or firewall it to trusted admin networks; use HTTPS at a reverse proxy.

**Restart recovery depends on the live tmux session:**
- Symptoms: `restart_server_process()` detects and respawns a dead server pane, while a missing or renamed tmux session/pane leaves the API without a recovery target.
- Files: `script/http_server.py`, `script/start_server.sh`
- Trigger: The tmux session is killed or its server pane is deleted or renamed.
- Workaround: Restart the container to recreate the managed session and panes.

## Security Considerations

**Plaintext administrative secret transport:**
- Risk: `RCON_PASSWORD` is submitted in JSON over HTTP and the generated token is accepted as bearer authority; port 5201 has no TLS.
- Files: `script/http_server.py:1019-1031`, `script/http_server.py:1381-1431`, `Dockerfile:14-16`
- Current mitigation: RCON endpoints are registered only when `RCON_PASSWORD` is set; RCON itself listens on `127.0.0.1`.
- Recommendations: Require HTTPS or private binding and use a separately provisioned random `ADMIN_AUTH_SECRET`.

**RCON command authority is broad:**
- Risk: Any authenticated caller can submit arbitrary Minecraft commands, including destructive administration commands.
- Files: `script/http_server.py:1181-1246`, `web-1.8/admin.js`, `web-1.12/admin.js`
- Current mitigation: Password/token authentication and local RCON binding.
- Recommendations: Use an allowlist for UI actions, reserve raw command execution for a separately protected operator endpoint, and audit commands.

**Unsigned and floating dependency supply chain:**
- Risk: The image includes prebuilt `.jar`, `.so`, `.class`, and client bundles; legacy `main.sh` downloads GitHub/Mojang/Paper assets at runtime.
- Files: `Dockerfile`, `main.sh:66-124`, `server-1.8/server.jar`, `server-1.12/server.jar`, `bungee/bungee.jar`, `script/libcubiomes_shim.so`
- Current mitigation: `main.sh` checks a Waterfall SHA256 before replacement.
- Recommendations: Pin versions and hashes for every artifact, build from a reproducible manifest, and remove runtime downloads from production startup.

## Performance Bottlenecks

**Thread-per-request HTTP service has no concurrency bound:**
- Problem: `ThreadingHTTPServer` creates request threads while RCON retries, Dynmap proxy calls, NBT reads, and structure scans run inline.
- Files: `script/http_server.py`, especially the structure scan, proxy, and server startup paths
- Cause: Concurrent expensive requests can retain many threads even though shared mutations are protected by locks.
- Improvement path: Keep the service private and low-volume; add bounded workers or a scan queue when measured concurrency requires it.

**Structure search scales quadratically with radius:**
- Problem: Region count grows with the square of `radius`; the maximum radius is 50,000 blocks across multiple structure types with viability checks.
- Files: `script/http_server.py:405-450`, `script/http_server.py:1330-1344`
- Cause: Every region is scanned synchronously and results are sorted after collection.
- Improvement path: Cache by seed/version/center/radius, cap work by estimated region count, and move large scans off the request thread.

**Dynmap player lookup multiplies upstream requests:**
- Problem: A lookup fetches configuration, then fetches one world endpoint per configured world.
- Files: `script/http_server.py:909-949`
- Cause: No cache or request budget covers the full world list.
- Improvement path: Cache world metadata briefly and query only known active worlds; retain the five-second upstream timeout.

## Fragile Areas

**Symlink and mount initialization:**
- Files: `script/start_server.sh`
- Why fragile: Startup mutates mount contents, refuses non-empty real directories, and legacy world linking depends on `level-name` and fallback names.
- Safe modification: Test empty mounts, populated mounts, existing symlinks, both versions, custom `level-name`, and simultaneous containers.
- Test coverage: `tests/test_regressions.py` covers invalid versions, preservation of incomplete mounts and regular active paths, Bungee-before-Paper ordering, and the tmux dead-pane respawn primitive.

**Hand-rolled NBT parser:**
- Files: `script/http_server.py:799-868`
- Why fragile: It implements only selected tag types and recursively parses persisted player data without explicit depth, count, or file-size limits.
- Safe modification: Add fixtures for each supported tag and malformed/truncated gzip/NBT data before changing parsing.
- Test coverage: No parser tests detected.

**Native ctypes bridge:**
- Files: `script/http_server.py:129-231`, `script/cubiomes_shim.c`, `script/libcubiomes_shim.so`
- Why fragile: Python ABI declarations must stay synchronized with the compiled C ABI; failures are deferred until a seed/structure request.
- Safe modification: Add a startup smoke check for required symbols and representative seeds for both `1.8` and `1.12`.
- Test coverage: No native bridge tests detected.

## Scaling Limits

**Fixed in-memory caches and process-local state:**
- Current capacity: Player markers cache for 2 seconds and world state cache for 1.5 seconds; state is held in module globals.
- Limit: Multiple HTTP processes or containers do not share cache state, and one process has no eviction or request coordination beyond the RCON lock.
- Scaling path: Keep one process for small deployments; use bounded external/cache coordination only after a measured multi-instance requirement.

**Embedded SQLite skin cache and fixed Java heaps:**
- Current capacity: Skin cache limits are configured at 32,768 objects/profiles; Bungee uses `-Xmx256M` and Paper uses the JVM defaults from `server-*/run.sh`.
- Limit: Large player counts, skin churn, or world growth can exhaust disk, heap, or file I/O capacity; no disk/heap monitoring is present.
- Scaling path: Add resource limits/metrics, size the JVM per deployment, and externalize or rotate cache data.

## Dependencies at Risk

**Paper/Waterfall 1.8.8 and 1.12.2 ecosystem:**
- Risk: These legacy server lines and bundled plugins receive limited modern security maintenance and run on an old Java/runtime base image.
- Impact: Protocol, plugin, and JVM vulnerabilities can remain latent while upgrade compatibility is constrained by Eaglercraft clients.
- Migration plan: Pin the base image and artifact hashes, scan jars, document the supported Java version, and maintain a tested upgrade matrix for both protocol versions.

**Vendored binary plugins and native libraries:**
- Risk: There is no repository manifest or automated compatibility check for bundled jars and `libcubiomes_shim.so`.
- Impact: Rebuilding or replacing one artifact can break startup or silently change gameplay/admin behavior.
- Migration plan: Record artifact provenance, SHA256, license, target Java/MC version, and a smoke-test command for every binary.

## Missing Critical Features

**Operational backup and restore:**
- Problem: World/plugin/config data is mutable and startup initialization can copy or rewrite mounted data, while no backup/restore workflow is documented or automated.
- Blocks: Reliable recovery after corruption, accidental commands, or failed upgrades.

**Container health metadata:**
- Problem: `script/start_server.sh` monitors Bungee, Paper, and HTTP and exits on failure, while `Dockerfile` defines no `HEALTHCHECK`.
- Blocks: Orchestrators from querying readiness or degraded state before a process exits.

## Test Coverage Gaps

**HTTP authentication and admin authorization:**
- What's not tested: Token expiry at the HTTP boundary, raw command authorization policy, and live RCON failure mapping.
- Files: `script/http_server.py:981-1031`, `script/http_server.py:1172-1503`
- Risk: A small auth or parser regression exposes RCON or crashes the management service.
- Priority: High

**Startup and persistence matrix:**
- What's not tested: Successful empty-mount initialization, EULA and RCON property writes, legacy world links, both successful version selections, real `TERM`/`INT` shutdown, and core-service failure propagation.
- Files: `script/start_server.sh`, `Dockerfile`, `server-1.8/`, `server-1.12/`
- Risk: Deployment failures or data loss appear only in production.
- Priority: High

**Seed search, NBT, Dynmap, and RCON protocol behavior:**
- What's not tested: Java/string seed conversion, radius limits, native bridge results, malformed NBT, Dynmap failures, RCON retries, packet framing, and concurrent requests.
- Files: `script/http_server.py:320-529`, `script/http_server.py:799-868`, `script/http_server.py:1082-1169`, `script/cubiomes_shim.c`
- Risk: Admin features return incorrect world data or block the only HTTP worker.
- Priority: Medium

**Dependency and image smoke tests:**
- What's not tested: Both Paper versions, Bungee plugin loading, required native symbols, exposed ports, and clean-container startup.
- Files: `Dockerfile`, `server-1.8/run.sh`, `server-1.12/run.sh`, `bungee/run.sh`
- Risk: Broken or incompatible bundled artifacts ship without detection.
- Priority: Medium

---

*Concerns audit: 2026-08-20*
