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

<!-- release-doc:live-example:start -->
```bash
./script/release_gate.sh \
  --build --live \
  --image eaglerx-release-gate:local \
  --evidence-dir artifacts/release-gate

./script/release_gate.sh \
  --live \
  --image ghcr.io/yangchuansheng/eaglerx1.8server:2.2.7
```
<!-- release-doc:live-example:end -->

`--live` makes an unavailable Docker daemon or any failed version a release
failure. Omitting `--live` records the Docker/Paper boundary as `skipped`.
The image check verifies that one image contains both Paper server trees and
both web roots. The image identifier, creation time, size, and selected
version are recorded as release evidence.

The live gate creates a fresh temporary full-runtime mount for each version
and uses a checked-in minimal JavaPlugin package. The package contains a
root-level `plugin.yml` and a no-op Paper plugin class, so the test does not
download a third-party artifact.

On Linux, the live gate needs permission to manage root-owned files created in
the temporary bind mount. The release workflow supplies that boundary through
passwordless `sudo` on the disposable GitHub-hosted runner.

For each selected version it performs:

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

## Documentation consistency

The same entry point checks the declared release, marked current runnable
examples and version guidance in all 14 READMEs, agent current-image/build
examples, this guide's live-image example, and release/verification links.
It uses the existing Python standard library and evidence writer, offline.

```bash
./script/release_gate.sh --docs-only
./script/release_gate.sh --docs-only --release-tag v2.2.7
```

Local checks default to the Verified Release Version in
[compatibility](compatibility.md). Tagged runs pass `--release-tag` from the
existing release-preparation outputs, including manual reruns of older tags.
A conflict, missing expected section/file, or broken evidence link fails with a
file and line. `--docs-only` writes evidence with `release_ready: false` and
cannot be combined with `--build` or `--live`. The normal gate always includes
this check before the existing complete automated checks.

`release-doc:ROLE:start/end` comments identify stable roles across translations:
`identity`, `quick-start`, `upgrade-target`, `version-guidance`, `release-command`,
`build-command`, `current-image`, and `live-example`. Keep each complete section
when editing. Runtime Minecraft, Paper, Java and plugin versions retain their
own meanings. Scope the following exemption tightly to a real earlier release
example; current required roles remain required outside exemptions:

```text
<!-- release-doc:migration-source:start -->
Earlier source image and its original release link belong here.
<!-- release-doc:migration-source:end -->
```

`historical` uses the same start/end syntax. Earlier verification files and ADRs
retain their original version references. Add a translated README to the checked
surface list when introducing a new translation.

## Manual evidence cadence

The initial C03 baseline requires real gameplay and recovery for Docker and the
pinned Sealos layout, both Game Versions. Follow the exact
[initial baseline procedure](verification/v2.2.7.md#initial-baseline-procedure).
The admin Mock API matrix and live plugin sentinel checks retain their existing
scope. Record failed/blocked scenarios as Unverified with a concrete finding;
keep runtime defect repairs separately reviewable.

| Change impact | Manual scenarios to execute |
| --- | --- |
| Client, connection, routing, startup | Fresh player setup, first join, return visit, second-network joining |
| Authentication or account handling | Fresh registration, return login, stable player identity, separate administrator access |
| Runtime, lifecycle, persistence, save, data layout | World/inventory continuity, independent backup and fresh-destination restoration |
| Migration, initialization, refresh, upgrade instructions | Exact same-Game-Version source/target upgrade and rollback |
| Operational procedure | Rerun the affected procedure and its observable player/data outcomes |
| Pure editorial correction | Focused version/link checks; retain the original execution dates |

For each release, record the compared source/template revisions, changed areas,
selected scenarios, and reasons any prior manual result still applies. Link
reused results by original release/date/configuration and label them reviewed
prior evidence. Each release still supplies new complete automated build/live
evidence. A passing automated `release_ready` reflects that existing gate;
manual acceptance status is recorded separately in the Release Verification Record.

## Durable records and release presentation

Before tagging, align the compatibility declaration, marked current examples,
and `docs/verification/vVERSION.md` with the intended Git tag. Record pending
fields and scenarios explicitly. After execution/publication, preserve the
sanitized summary and relevant evidence rows with the versioned documentation;
add the source commit, published digest, template revision, environment, actual
runtime Java/Paper identities, dates, outcomes, and limits. Keep a permalink to
the resulting documentation commit. Historical executions retain their dates
and artifact identities even when documentation is updated later.

The release job summary supplies links to the compatibility and version-specific
record. Add those durable links to the existing GitHub Release along with concise
change-impact, migration/rollback status, and the
[Sealos deployment handoff](https://sealos.io/products/app-store/eaglercraft-server/).
The [current record](verification/v2.2.7.md#release-presentation) includes prepared
release text. A temporary Actions artifact is supporting evidence; retain its
sanitized results before expiry. Larger sanitized captures may be release assets.
Never publish credentials, raw authentication requests, private player data or
unreviewed server logs.
