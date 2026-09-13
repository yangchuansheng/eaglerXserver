# Sealos execution: 2026-09-13

This record supplements the original Docker gate with real clients and disposable
Sealos workloads. **C03 acceptance remains incomplete:** Docker full-runtime
manual recovery/migration needs its own execution. Status applies to each named
scenario below.

## Execution identity

- Operator: Codex, controlling both real browser clients through native input.
- Region: Sealos US West; Linux AMD64 runtime. The user authorized the current
  workspace and cleanup of the run's own workloads and volumes.
- Release: v2.2.7, source `fe33def8a9089412ab62d972d81bad97ab0bb145`.
- Both main and init image: `ghcr.io/yangchuansheng/eaglerx1.8server:2.2.7@sha256:56ad224a996030b7bfb2837702f065fe88685eda511d7a186812f22dc5cad047`.
- Template: [7102fcf6ed3ad666a405cb442cc5ac446ebf8bdc](https://github.com/yangchuansheng/templates/blob/7102fcf6ed3ad666a405cb442cc5ac446ebf8bdc/template/eaglercraft-server/index.yaml).
  The initial deployment changed only generated application/host names and the
  declared Game Version/admin-password inputs. Separate 1 GiB PVCs and the
  template's 200m CPU / 1024Mi main-container limits were retained.
- Primary browser: Chrome 152.0.7977.84 on macOS, separate saved profile per Game
  Version. Bundled client footers: EaglercraftX 1.8-u7 and Eaglercraft 1.12.2 (u1),
  WASM-GC. The compiled client payloads are unchanged across the recorded release pair;
  HTML entry pages and 1.8 client options changed and were refreshed by init.
- Second browser: Chromium bundled in `mcr.microsoft.com/playwright:v1.63.0-noble`,
  in a separate Sealos Pod. It used the public HTTPS/WSS ingress, with a network
  origin separate from the macOS browser. Debugging remained private. CPU was
  increased from 1 to 4 cores after software rendering saturated the initial
  limit; memory stayed at 2 GiB. Later 1.12 recovery and migration checks used
  this browser with a 640 × 360 viewport and the original `C03Player112` profile
  name, after closing the macOS client. Both clients were operated by the same agent.
- Runtime Java, both Game Versions: OpenJDK 11.0.23, build
  `11.0.23+9-post-Ubuntu-1ubuntu122.04.1`, 64-bit.
- Paper 1.8: `git-PaperSpigot-445 (MC: 1.8.8)`, API `1.8.8-R0.1-SNAPSHOT`.
- Paper 1.12: `git-Paper-1620 (MC: 1.12.2)`, API `1.12.2-R0.1-SNAPSHOT`.
- Proxy/authentication bundled identities: BungeeCord build 1889,
  EaglercraftXBungee 1.3.6, LoginSecurity 3.2.0. See the parent record's manifest
  and asset identities; gameplay traversed that proxy and authentication stack.

Public evidence contains only throwaway test player names and test-world data.
Admin/player passwords, tokens, full rendered manifests, and recovery archives
are retained privately. Screenshots show actual client rendering and server
responses. Admin/RCON commands seeded the countable items and world markers.
[Machine observations](observations.json) retain UTC API observations, selected
state snapshots, running image IDs where captured, and screenshot retention times.

## Scenario results

| Scenario | Game 1.8 | Game 1.12 | Evidence / scope |
| --- | --- | --- | --- |
| Paper readiness and separate protected admin login | Runtime-verified | Runtime-verified | Public status and authenticated admin API; runtime version responses |
| Fresh browser registration | Runtime-verified | Runtime-verified | LoginSecurity `/register`; [1.12 first registration](1.12-registration.png) |
| Logout and return login | Runtime-verified | Runtime-verified | Real `/logout` then `/login`; [1.12 return](1.12-return-login.png) |
| Paper restart, return login, home and three diamonds | Runtime-verified | Runtime-verified | [1.8](1.8-paper-restart.png), [1.12](1.12-paper-restart.png) |
| Two network origins concurrently online | Runtime-verified | Runtime-verified | Authenticated `list` returned two players; separate cloud browser registration/login |
| Other player visibly present in the same world | Runtime-verified | Unverified | [1.8 two players](1.8-two-players.png); 1.12 concurrent list and remote world entry are narrower observations |
| Fresh PVC restoration into a replacement workload | Runtime-verified | Runtime-verified | [1.8 recovered world, inventory and home](1.8-fresh-pvc-restore.png); [1.12 original login, inventory and home](1.12-fresh-pvc-restore.png) |
| Release Upgrade 2.2.5 to 2.2.7, same Game Version | Runtime-verified | Runtime-verified | [1.8 source](1.8-upgrade-source-2.2.5.png), [1.8 target](1.8-upgraded-2.2.7.png), [1.12 source](1.12-upgrade-source-2.2.5.png), [1.12 target](1.12-upgraded-2.2.7.png) |
| Rollback to retained 2.2.5 source-period data | Runtime-verified | Runtime-verified | [1.8 rollback](1.8-rollback-2.2.5.png), [1.12 rollback after a fresh-page retry](1.12-rollback-2.2.5.png); client crash retained below |

At 2026-09-13T08:43:51Z the 1.8 admin list contained `YeeishYeae812` and
`YeeishVigg612`; [the cloud client](1.8-second-network-login.png) also reported
successful login and an authenticated `/homes` response. At
2026-09-13T09:06:06Z the 1.12 list contained `C03Player112` and `YeeishVigg5258`;
[the cloud client](1.12-second-network-registration.png) reported successful
registration and an authenticated `/homes` response. This verifies two browser
connections from the stated network locations, under one operator.

The observed first-visit route was bundled profile setup, Multiplayer, then
LoginSecurity's in-world `/register <password>` prompt. Return visits used
`/login <password>`. A separate proxy `/eagler` setup screen did not appear in
these executions. The generated 1.12 profile also displayed its username warning
and client attribution notice before Multiplayer.

## Recovery method and retained state

The writer StatefulSet was scaled to zero and Pod deletion was awaited. A
one-off helper mounted the source PVC read-only, a separate backup PVC, and a
fresh destination PVC. It archived all of `/eaglerx-data`, then extracted that
archive into the fresh destination before starting the restored workload. The
empty ext4 destination contained only its filesystem-created `lost+found`.
Full rendered StatefulSet, ConfigMap, Service and Ingress configurations were
retained privately. The replacement used the same image, template scripts,
mount paths and environment. Its new workload/PVC names and Service selector
were the recovery overlay; the public host stayed constant so the saved browser
profile and player name were preserved.

The source, backup and destination were distinct PVCs. This storage class uses
node affinity, so each Game Version used its own independently provisioned
backup PVC on a compatible node. A helper attempting to combine volumes pinned
to different nodes remained unschedulable; that attempt wrote no archive.
Off-cluster retention and final cleanup are recorded below.

The persistence fixture used three diamonds, a `c03` home and a gold block at
`(-184, 70, 290)` for 1.8 or `(100, 64, 180)` for 1.12. Later retention checks used
Creative mode and peaceful difficulty to keep survival events separate from
storage comparisons. The fixture's player UUID, inventory count, home contents,
operator/whitelist files and authentication/plugin configuration are compared
across the retained source and destination snapshots. Empty operator/whitelist
files establish empty-list continuity only.

For 1.8, the restored client visibly retained the gold block, three diamonds and
`c03`, and completed login using the original password. RCON `testforblock`
confirmed the same coordinate. The player's UUID remained
`8e47504a-19a7-3d2b-811c-a31939180a69` through restoration and upgrade.

## Release-pair configuration

Source release commit: `65e553d03a455f79bbf4d0863a92fe03f98fb904`.
The source image is
`ghcr.io/yangchuansheng/eaglerx1.8server:2.2.5@sha256:4182f021393cbbded567297b98cffde1970090f10d912dc9116d051130e7b14c`.
The source workload was seeded from the independently restored test data and
then started with the 2.2.5 main/init images. The pinned template's init step
loaded 2.2.5 scripts and web roots before source validation. The Git comparison
`v2.2.5..v2.2.7` contains no changes under `bungee/`, `server-1.8/`, or
`server-1.12/`; compiled game payload assets are also unchanged. HTML entry pages and 1.8
client options changed, so source and target init steps refreshed those files.
This bounds the
init-refresh migration tested here.

After successful source login and state inspection, that 2.2.5 source was
stopped and archived independently. A fresh target PVC received the source-period
archive and started with 2.2.7 main/init images. Target login, inventory, home and
world state were checked. Rollback starts the retained stopped 2.2.5 source PVC
with its source image and repoints the Service, preserving target-period writes
on the separate target volume. This records a same-Game-Version release pair;
world conversion and changes to server/plugin binaries need their own migration.

## Observed limitations and cleanup

Initial automation attempts encountered cloud rendering saturation, transient
TLS/port-forward failures, handshake failures and the 30-second login timeout.
Successful retries used native key events after world entry, and cloud-side
input execution. These retries retain their test-tool/network boundary.

An early 1.12 disposable account died during setup and subsequently reached a
death screen while the login timer expired. Recovery from that mortality/login
state was not isolated or verified. The controlled `C03Player112` fixture then
completed the recorded registration, return and restart checks. Mortality and
respawn behavior remain an explicit unverified edge case; this documentation
change makes no runtime repair claim.

A 1.12 rollback reconnect also displayed an [unexpected client
NullPointerException](1.12-rollback-client-crash.png). A fresh page using the same
player name then logged in with the original password and retained three diamonds
and `c03`. The crash trigger remains unisolated; this successful retry establishes
state recovery while client reconnect reliability remains an open limitation.

All four stopped-runtime archives (both 2.2.7 recovery sources and both 2.2.5
upgrade sources) were retained off-cluster with source-matching SHA-256 checksums.
They and the rendered configurations remain private. The selected source-period
snapshots exactly match the upgraded and rolled-back snapshots for both Game
Versions, including UUID, inventory, position, homes and selected configuration
hashes. The original 1.12 recovery snapshot and fresh-PVC snapshot also match.
The 1.8 fresh-PVC result is supported by its login screenshot and world probe.

Cleanup completed at 2026-09-13T14:44:13.596769+00:00.
[Cleanup evidence](cleanup.json) records deletion of the six test StatefulSets,
eight PVCs, helper/browser Pods, routes, configuration, and Sealos App/Instance
records. A final inventory found zero resources with this run's names. The
original public test hosts are retired. Target-period test volumes were retained
through rollback and then removed under the user's cleanup authorization.
