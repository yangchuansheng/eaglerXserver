---
phase: 04-mirror-gate-and-release-matrix
plan: "02"
subsystem: release-gate
tags: [browser, mock-api, agent-browser, cleanup]
requires:
  - phase: 04-mirror-gate-and-release-matrix
    plan: "01"
    provides: exact mirrored release assets and direct-root static gate
provides:
  - deterministic two-root served browser release matrix
  - sanitized raw-output and responsive evidence rows
  - explicit mock and deployment-environment boundaries
affects: [phase-4-verification]
actuals:
  tasks: 2
  commits: 1
tech-stack:
  added: []
  patterns: [standard-library mock HTTP server, isolated agent-browser session, temporary profile and policy]
key-files:
  created: [tests/test_browser_release_matrix.py, .planning/phases/04-mirror-gate-and-release-matrix/04-02-SUMMARY.md]
requirements-completed: [PARI-01, PARI-03]
status: complete
---

# Phase 4 Plan 02: Browser Release Matrix Summary

## Accomplishments

- Added a dependency-free local Mock Admin API with token-gated status, login, command, configuration, world, runtime, seed, structure, and player-location routes.
- Added one identical served browser scenario for `web-1.8` and `web-1.12`: English first paint, zh-CN persistence, login refresh, dialog validation/state survival, command notification, exact raw rendering, controlled error, recovery, and desktop/mobile layout checks.
- Added named isolated browser sessions, temporary profiles and default-deny action policies, content boundaries, local/font domain allowlists, per-command and per-root deadlines, and sanitized English evidence rows.

## Verification

- `python3 -m unittest tests.test_browser_release_matrix.MockAdminServerTests -v` — 1 passed.
- `agent-browser doctor` — 14 pass, 0 warn, 0 fail; local headless launch passed.
- `python3 -m unittest tests.test_browser_release_matrix.BrowserReleaseMatrixTests -v` — 1 passed for both roots in 25.804 seconds.

## Cleanup and Evidence

- The fixture password and token are process-local. Raw fixture and controlled-error text are assembled only at runtime; evidence contains SHA-256 digests and UTF-8 byte lengths.
- `finally` closes the isolated browser session, clears its named state, stops and joins the loopback server, and deletes each temporary profile, policy, screenshot, and diagnostic directory.
- The browser matrix reports `browser-release-matrix: deterministic local Mock Admin API` for every evidence row.

## Environment Boundary

`deployment-boundary: live Docker/Paper/Waterfall/RCON not exercised`

## Product Scope

Product assets remained frozen. The controlled backend-error scenario recovered through the existing client path, so no in-scope product fix was required.

## Self-Check: PASSED
