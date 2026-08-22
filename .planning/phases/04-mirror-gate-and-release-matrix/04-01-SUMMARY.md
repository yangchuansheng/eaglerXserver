---
phase: 04-mirror-gate-and-release-matrix
plan: "01"
subsystem: release-gate
tags: [mirror, locale, static-http, regression]
requires:
  - phase: 03-dynamic-renderers-and-raw-output-boundary
    provides: mirrored localized administration assets and raw-output contract
provides:
  - exact five-asset SHA-256 mirror diagnostics
  - direct-root locale/catalog/runtime release contract
  - isolated served administration static-entrypoint coverage
affects: [phase-4-browser-release-matrix]
actuals:
  tasks: 2
  commits: 1
tech-stack:
  added: []
  patterns: [standard-library loopback server, Node VM locale evaluation, direct-version-root testing]
key-files:
  created: [.planning/phases/04-mirror-gate-and-release-matrix/04-01-SUMMARY.md]
  modified: [tests/test_regressions.py]
requirements-completed: [PARI-01, PARI-02]
status: complete
---

# Phase 4 Plan 01: Mirror and Static Release Gate Summary

## Accomplishments

- Added exact byte parity checks for all five released administration assets, including SHA-256 diagnostics on drift.
- Added bilingual locale, catalog, inventory-reference, fallback, interpolation, missing-marker, and locale interaction checks for both direct versioned roots.
- Added isolated loopback static coverage for the game root and `/admin`, `/admin/`, and `/admin.html` administration entrypoints.

## Verification

- `python3 -m unittest tests.test_regressions.ReleaseContractTests tests.test_regressions.ServedAdminStaticTests -v` — 3 passed.
- `node --check` for both mirrored administration and i18n scripts — passed.
- Exact `cmp -s` checks for all five mirrored release assets — passed.
- `git diff --check` — passed.

## Deviations from Plan

The game root remains the shipped game entrypoint. The static matrix verifies its successful response separately, then validates administration-shell content through `/admin.html` and both redirect routes.

## Environment Boundary

This gate uses direct versioned static roots and an ephemeral loopback server. Docker, Paper, Waterfall, and RCON remain outside this test boundary.

## Self-Check: PASSED
