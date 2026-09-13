# Delivered-image compatibility

Verified Release Version: `v2.2.7`

The [maintained source repository](https://github.com/yangchuansheng/eaglerXserver)
owns the Release Image, Git tags, and runtime checks.
[Release v2.2.7](https://github.com/yangchuansheng/eaglerXserver/releases/tag/v2.2.7)
is the current documentation baseline. **Verified applies to the named scenarios
below. The complete C03 gameplay and recovery baseline remains Unverified.**

- Source commit: `fe33def8a9089412ab62d972d81bad97ab0bb145`.
- Release Image: `ghcr.io/yangchuansheng/eaglerx1.8server:2.2.7`.
- Published digest: `sha256:56ad224a996030b7bfb2837702f065fe88685eda511d7a186812f22dc5cad047`.
- Publication platform: Linux AMD64 (`linux/amd64`).
- [Release Verification Record](verification/v2.2.7.md): dates, source identities,
  durable automated evidence, scenario outcomes, and open acceptance work.

A **Release Version** identifies the entire image. A **Game Version** selects
one world lineage: `MINECRAFT_VERSION=1.8` selects Paper 1.8.8;
`MINECRAFT_VERSION=1.12` selects Paper 1.12.2. Component versions identify the
individual binaries and clients. Git tags remain the release authority.

## Evidence vocabulary

| Status | Meaning |
| --- | --- |
| Source-confirmed | Read from a pinned source, bundled asset, manifest, or deployment configuration |
| Runtime-verified | The named scenario ran against the stated artifact and configuration on the recorded date |
| Unverified | Execution evidence is missing, incomplete, or blocked; retain the limitation until the scenario passes |

A **Verified Configuration** binds an image digest, architecture, selected Game
Version, deployment layout, component identities, and named scenario results.
External Java servers, arbitrary clients, ARM64, and cross-Game-Version world
conversion each require their own integration evidence.

## Compatibility matrix

All rows use the release, source, digest, and architecture declared above.
Component identities and asset hashes are in the linked record. The Sealos run
on 2026-09-13 observed OpenJDK 11.0.23+9, PaperSpigot 445 for 1.8.8, and Paper
1620 for 1.12.2. The prior Docker output omitted these running-build fields.

| Configuration | Game Version / Paper | Bundled client | Components | Scenario status and original date | Evidence |
| --- | --- | --- | --- | --- | --- |
| Docker full runtime mount | 1.8 / 1.8.8 | EaglercraftX 1.8; source/asset identity | BungeeCord build 1889; EaglercraftXBungee 1.3.6; LoginSecurity 3.2.0; runtime Java Unverified | Runtime-verified: Paper readiness, protected admin API, plugin lifecycle and container replacement, 2026-09-09; gameplay/recovery Unverified | [Docker evidence](verification/v2.2.7.md#automated-execution) |
| Docker full runtime mount | 1.12 / 1.12.2 | Eaglercraft 1.12 WASM-GC; source/asset identity | Same proxy/authentication components; runtime Java Unverified | Runtime-verified: same automated scenarios, 2026-09-09; gameplay/recovery Unverified | [Docker evidence](verification/v2.2.7.md#automated-execution) |
| Pinned Sealos template | 1.8 / PaperSpigot 445, 1.8.8 | EaglercraftX 1.8-u7 | OpenJDK 11.0.23+9; same proxy/authentication components | Runtime-verified named gameplay, restart, fresh-PVC recovery, release-upgrade and rollback scenarios, 2026-09-13 | [Sealos execution](verification/v2.2.7-evidence/sealos/README.md) |
| Pinned Sealos template | 1.12 / Paper 1620, 1.12.2 | Eaglercraft 1.12.2 (u1), WASM-GC | OpenJDK 11.0.23+9; same proxy/authentication components | Runtime-verified named registration, return-login, Paper-restart, fresh-PVC recovery, release-upgrade and rollback scenarios, 2026-09-13; remaining scenario results recorded separately | [Sealos execution](verification/v2.2.7-evidence/sealos/README.md) |

The manifest in `bungee/bungee.jar` identifies BungeeCord build 1889, commit
`7340f1a`, version `1.21-R0.1-SNAPSHOT`. Earlier Waterfall labels describe the
repository's history. `Build-Jdk-Spec: 17` describes the proxy's build toolchain.
Read `java -version` inside the running container for runtime Java evidence.

## Configuration and access boundaries

**Docker:** follow the [quick start](../README.md#quick-start). The Persistent
Runtime Directory is mounted in full at `/eaglerX-1.8-server`. Empty mounts receive
the image template; existing complete mounts retain their own runtime code and
state. Each concurrent Game Version needs an independent host directory. Port
5200 serves the Game Entry and WebSocket Game Address. Port 5201 binds to host
loopback for the Management Plane; remote administrators use an SSH tunnel, VPN,
or protected HTTPS proxy. Wait for **Paper is ready** before game validation.

**Sealos:** the configuration authority is
[template revision 7102fcf6ed3ad666a405cb442cc5ac446ebf8bdc](https://github.com/yangchuansheng/templates/blob/7102fcf6ed3ad666a405cb442cc5ac446ebf8bdc/template/eaglercraft-server/index.yaml).
It pins the same image digest in both containers. The PVC mounts `/eaglerx-data`;
`APP_DIR=/eaglerx-data/runtime` and
`PERSISTENT_DATA_ROOT=/eaglerx-data/runtime/server-data`. An init container seeds
an empty runtime or refreshes scripts and both web roots in an existing runtime.
Existing Paper trees, plugin repositories, authentication data, and worlds stay
on the volume. Keep custom frontend copies outside the refresh destinations.
One instance owns one Game Version and one PVC. The initial PVC is 1 GiB; the
main container limits are 200m CPU and 1024Mi memory.

The template routes `/` and WSS to 5200; `/admin`, `/api`, admin assets, and
`/dynmap` use HTTPS ingress to 5201. This is the template's externally routed
Management Plane. Administrative API access requires the administrator session;
protect the admin route and Dynmap with your platform's access policy. Readiness
requires the initial world save and reachable runtime ports; the service exposes
the loading console while startup continues. The ingress upload ceiling is
32 MiB. These are source-confirmed template facts.

## Player onboarding and identity

The **Game Entry** loads the selected bundled client. A **Quick Join Link** adds
`?server=ws://.../` or `?server=wss://.../` to select its multiplayer destination.
A compatible existing client accepts the **WebSocket Game Address** in its
Multiplayer server list. Set a stable player profile name before following a
Quick Join Link; the initial client profile may contain a generated name.

Both source trees configure LoginSecurity registration, `/register <password>`,
`/login <password>`, a 6–32 character password, and a 30-second login window.
The proxy also enables its onboard authentication system in
`bungee/plugins/EaglercraftXBungee/authservice.yml`, with support for a pre-join password
prompt and `/eagler` account setup. In both pinned Sealos configurations tested
on 2026-09-13, the bundled client entered Paper and displayed the LoginSecurity
`/register` prompt directly. Return visits displayed `/login`. That run observed
no separate proxy account-setup screen. Docker onboarding still needs a named
real-client execution.

Player Account credentials protect the player's identity. `RCON_PASSWORD`
authenticates an administrator to the Management Plane. A return visit must
verify the same player identity, world position/state, and inventory. The
[initial acceptance procedure](verification/v2.2.7.md#initial-baseline-procedure)
covers those observations and a second player on another network.

## Recovery and release upgrades

A **World Recovery Copy** is a separately retained, consistent copy of the
worlds, identity/authentication data, plugin data, and retained configuration.
Stop the writer, archive the full persistent layout including external symlink
targets, then restore into a fresh destination. Preserve the original data and
record login, world, and inventory results after restoration.

A **Release Upgrade** changes the Release Version while keeping the Game Version.
Use the [Docker backup, restore, upgrade and rollback procedure](../README.md#backups-upgrades-and-rollbacks).
For Sealos, archive the entire `/eaglerx-data` volume while the StatefulSet is
scaled to zero, plus a private copy of the rendered workload/configuration.
Restore into a fresh PVC attached to a separate stopped instance with the same
Game Version, image digest and template revision. Validate the restored source
release before applying the target image/template to this copy. Keep the
original PVC and rendered source configuration for rollback. The init container
refreshes scripts/web assets on startup; changes to server/plugin binaries or
data layouts require an explicit migration review.

The exact recorded release pair and all recovery/upgrade results are tracked in
the verification record. Complete gameplay, recovery, and rollback acceptance
before claiming the selected deployment configuration is verified.

After choosing a configuration and reviewing its evidence, continue to the
[Sealos Eaglercraft deployment template](https://sealos.io/products/app-store/eaglercraft-server/).
