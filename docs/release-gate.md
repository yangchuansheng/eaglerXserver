# Release gate

`script/release_gate.sh` is the repeatable release gate for plugin management.
It uses Python's standard library and adds no runtime dependency.

## Local gate

Run the deterministic checks from the repository root:

```bash
./script/release_gate.sh --evidence-dir artifacts/release-gate
```

The local gate runs Python syntax compilation, the complete server/plugin
regression suite, the bilingual browser matrix for `web-1.8` and `web-1.12`,
and the static dual-version/mirrored-asset checks. The browser rows use a
deterministic local Mock Admin API. A passing local gate reports a live
boundary and has `release_ready: false` in `summary.json`.

## Build and live gate

Use a disposable image tag for a build check, or point the gate at an existing
image:

```bash
./script/release_gate.sh \
  --build --live --require-live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate

./script/release_gate.sh \
  --live --require-live \
  --image registry.cn-hangzhou.aliyuncs.com/chenxuan/eaglerx1.8server:2.1
```

`--require-live` makes an unavailable Docker daemon or any failed version a
release failure. Without `--require-live`, omitting `--live` records the
Docker/Paper boundary as `skipped`; the command never claims live coverage.
The image check verifies that one image contains both Paper server trees and
both web roots. The image identifier, creation time, size, and selected
version are recorded as release evidence.

The live gate creates a fresh temporary full-runtime mount for each version
and uses a generated minimal JavaPlugin package. The package contains a
root-level `plugin.yml` and a no-op Paper plugin class, so the test does not
download a third-party artifact. For each selected version it performs:

1. Start a mounted container with `MINECRAFT_VERSION` and a throwaway RCON
   password, then verify `/api/status` and the Paper `version` command.
2. Upload the package through `/api/plugins/upload`, verify the 64 MiB limit,
   verify the package appears in the repository inventory, restart Paper, and
   verify the package appears in the runtime plugin list.
3. Disable and enable the package. The runtime plugin list must keep its old
   state until `/api/system` performs the controlled Paper restart.
4. Delete the package, restart, verify it leaves the runtime, and verify the
   repository data directory remains. Re-upload the same filename, restart,
   and verify the data remains available.
5. Stop the first container, start a replacement with the same mount, and
   verify repository state, Paper runtime state, and retained data.

The gate always removes test containers and temporary mounts, including after a
failed check. The temporary mount contains a test sentinel and must be treated
as disposable.

## Evidence boundary

Each run writes a unique directory containing `evidence.jsonl` and
`summary.json`. Rows contain statuses, version labels, container mount
boundaries, SHA-256 digests, byte counts, image metadata, and API/browser/Paper
result labels. The evidence writer drops credential, token, authorization,
raw response, command, and plugin-data fields; the summary explicitly records
`credentials_recorded: false` and `plugin_data_recorded: false`.

Do not redirect Docker logs, HTTP bodies, browser snapshots, or environment
variables containing credentials into the evidence directory. Failed checks
record only an error digest and byte count. Treat the temporary mount as
private test data and remove it after inspection.

## Deployment invariants

### Version-isolated repositories

`MINECRAFT_VERSION` accepts `1.8` or `1.12` and selects one server/web pair per
container. The persistent data root contains independent repositories:

```text
<PERSISTENT_DATA_ROOT>/plugins-1.8/
<PERSISTENT_DATA_ROOT>/plugins-1.12/
```

Packages and plugin data stay inside the selected version's repository. Run
parallel versions with separate host directories and host ports so operators
cannot accidentally share a live world or plugin state:

```text
/data/eagler-1.8  -> MINECRAFT_VERSION=1.8
/data/eagler-1.12 -> MINECRAFT_VERSION=1.12
```

### Persistent mounts

The supported full-runtime mount is:

```text
-v /data/eagler-1.12:/eaglerX-1.8-server
```

An empty directory is initialized from the image. A non-empty incomplete
directory is preserved and rejected. `PERSISTENT_DATA_ROOT` can point to a
separate mounted data directory for worlds and version-scoped plugin
repositories; `SERVER_DATA_DIR` remains a compatibility alias.

### Uploads and restart semantics

Plugin upload accepts one regular JAR with a root-level `plugin.yml` and a
maximum body size of 64 MiB. Upload, enable, disable, and delete operations
write a pending-restart marker. Paper reads the selected `enabled` directory
at its next explicit restart; the API does not hot-reload arbitrary plugin
code. Use the admin restart action or the authenticated endpoint:

```json
{"action":"restart_server","token":"<session token>"}
```

A failed controlled restart keeps the marker so the operator can retry and
inspect the server. A successful controlled restart clears it after Paper is
running.

Deleting a package removes its JAR and preserves its sibling plugin-data
directory. Reinstalling the same package filename can therefore reuse the
retained configuration/database state. Back up the repository before package
replacement and inspect plugin-specific migration behavior.

### Custom-code warning

Every uploaded or bundled plugin JAR executes arbitrary code in the Paper JVM
with the container's available permissions. Accept packages only from a
trusted source, review and scan them, restrict the container filesystem and
network, and keep a recoverable data backup. The upload validation checks the
archive boundary and `plugin.yml`; it cannot certify plugin behavior.

### Management-plane boundary

Port 5201 serves the authenticated local management plane and binds to the
host loopback address in the deployment examples. Keep it private. Remote
administrators must use an HTTPS reverse proxy, a VPN, or an SSH tunnel to the
loopback service. Plain HTTP on a public interface is not a supported remote
transport. Port 5200 remains the public game/client entry point.

The `web-1.8` and `web-1.12` admin assets are mirrored byte-for-byte and ship
inside the same image. The gate checks this parity before any live smoke.
