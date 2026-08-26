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
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate

./script/release_gate.sh \
  --live \
  --image ghcr.io/yangchuansheng/eaglerx1.8server:2.2
```

`--live` makes an unavailable Docker daemon or any failed version a release
failure. Omitting `--live` records the Docker/Paper boundary as `skipped`.
The image check verifies that one image contains both Paper server trees and
both web roots. The image identifier, creation time, size, and selected
version are recorded as release evidence.

The live gate creates a fresh temporary full-runtime mount for each version
and uses a checked-in minimal JavaPlugin package. The package contains a
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
boundaries, SHA-256 digests, byte counts, and image metadata. The evidence
writer drops credential, token, authorization, raw response, command, and
plugin-data fields; the summary explicitly records
`credentials_recorded: false` and `plugin_data_recorded: false`.

Do not redirect Docker logs, HTTP bodies, browser snapshots, or environment
variables containing credentials into the evidence directory. Failed checks
record only an error digest and byte count. Treat the temporary mount as
private test data and remove it after inspection.

## Deployment invariants

See the root `README.md` and `AGENTS.md` for the canonical mount, repository,
restart, custom-code, and management-plane boundaries.
