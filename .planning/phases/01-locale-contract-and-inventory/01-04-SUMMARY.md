---
phase: 01-locale-contract-and-inventory
plan: "04"
subsystem: i18n
tags: [i18n, inventory, regression, mirror]
requires:
  - phase: 01-locale-contract-and-inventory
    provides: mirrored locale inventory and runtime
provides:
  - Exact literal-level source-to-inventory coverage for protected admin HTML and JavaScript
  - Bilingual catalog parity for every presentation source surface
  - Regression checks for missing, duplicate, stale, corrupt, and operational catalog links
affects: [phase-2-static-shell, phase-3-dynamic-renderers, phase-4-mirror-gate]
actuals:
  tokens: 624019
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [literal-level source tuple inventory, exact catalog-key parity]
key-files:
  created: [.planning/phases/01-locale-contract-and-inventory/01-04-SUMMARY.md]
  modified: [web-1.8/admin-i18n-inventory.json, web-1.12/admin-i18n-inventory.json, web-1.8/admin-i18n.js, web-1.12/admin-i18n.js, tests/test_regressions.py]
key-decisions:
  - "Use the exact (file, line, column, literal, lineText) tuple set as the source coverage contract."
  - "Keep operational records catalog-free while preserving the existing raw command and safe-rendering boundary assertions."
requirements-completed: [CORE-01, SAFE-03]
coverage:
  - id: D1
    description: Every scoped Han-script source literal has one exact presentation surface and catalog key.
    requirement: CORE-01
    verification:
      - kind: unit
        ref: tests/test_regressions.py#I18nInventoryTests.test_client_authored_source_coverage_is_regressible
        status: pass
    human_judgment: false
  - id: D2
    description: Missing, duplicate, stale, corrupt, and incorrectly linked source surfaces fail closed.
    requirement: CORE-01
    verification:
      - kind: unit
        ref: tests/test_regressions.py#I18nInventoryTests.test_source_surface_contract_rejects_missing_duplicate_and_corrupt_mappings
        status: pass
    human_judgment: false
  - id: D3
    description: Presentation catalogs are complete and operational keys remain catalog-free.
    requirement: SAFE-03
    verification:
      - kind: unit
        ref: tests/test_regressions.py#I18nRuntimeTests.test_catalog_contract_rejects_missing_extra_and_operational_keys
        status: pass
    human_judgment: false
duration: 12min
completed: 2026-08-20
status: complete
---

# Phase 1 Plan 04: Literal-Level Inventory Gap Closure Summary

**The mirrored locale contract now maps all 906 scoped Han-script literals to exact source evidence and catalog records.**

## Performance

- **Duration:** 12 min
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Replaced line-count and SHA-256 coverage evidence with 906 exact source surfaces: 281 from `admin.html` and 625 from `admin.js`.
- Added non-empty English and Simplified Chinese catalog values for all 906 presentation keys, preserving 8 catalog-free operational records.
- Added direct regression checks for exact source tuples, duplicate IDs/tuples/keys, stale locations, corrupted links, catalog gaps, extra keys, and operational catalog leakage.

## Task Commits

1. **Task 1: Replace hash-only coverage with an exact literal-level inventory and bilingual catalog** - `b529674` (`feat`)
2. **Task 2: Make literal-level coverage and catalog completeness fail closed** - `0d11909` (`test`)

## Files Created/Modified

- `web-1.8/admin-i18n-inventory.json` - Canonical literal-level inventory.
- `web-1.12/admin-i18n-inventory.json` - Byte-identical inventory mirror.
- `web-1.8/admin-i18n.js` - Complete English and Simplified Chinese catalogs.
- `web-1.12/admin-i18n.js` - Byte-identical runtime mirror.
- `tests/test_regressions.py` - Exact surface, catalog, operational-boundary, and parity regression checks.

## Verification

- `python3 -m unittest tests.test_regressions.I18nInventoryTests tests.test_regressions.I18nRuntimeTests -v` — 9 passed.
- `python3 -m unittest discover -s tests -p 'test_*.py'` — 24 passed.
- `node --check web-1.8/admin.js && node --check web-1.12/admin.js && node --check web-1.8/admin-i18n.js && node --check web-1.12/admin-i18n.js` — passed.
- Inventory/runtime mirrors and all six protected admin root-pair checks — passed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

G-01-1 has executable closure evidence. Phase 1 verification and Phase 2 remain outside this execution.

## Self-Check: PASSED
