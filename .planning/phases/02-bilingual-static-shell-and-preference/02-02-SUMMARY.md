---
phase: 02-bilingual-static-shell-and-preference
plan: "02"
subsystem: i18n
tags: [i18n, static-bindings, inventory, mirror]
requires:
  - phase: 02-bilingual-static-shell-and-preference
    provides: locale preference and DOM-only lifecycle
provides:
  - Explicit bilingual bindings for the static administration shell
  - Exact static-binding source contract with bilingual catalog checks
  - Full mirrored asset and regression gate
affects: [phase-3-dynamic-renderers, phase-4-mirror-gate]
actuals:
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [explicit-data-i18n-bindings, static-binding-inventory-contract, byte-identical-mirrors]
key-files:
  created: [.planning/phases/02-bilingual-static-shell-and-preference/02-02-SUMMARY.md]
  modified: [web-1.8/admin.html, web-1.8/admin-i18n-inventory.json, web-1.8/admin-i18n.js, tests/test_regressions.py]
key-decisions:
  - "Static binding inventory records exact English source locations independently from deferred dynamic renderer literals."
requirements-completed: [COVR-01, COVR-05]
coverage:
  - id: D1
    description: Static source copy, metadata attributes, and iframe title resolve through explicit bilingual bindings.
    requirement: COVR-01
    verification:
      - kind: unit
        ref: tests/test_regressions.py#StaticShellLocaleTests.test_static_binding_contract_has_exact_sources_and_bilingual_keys
        status: pass
    human_judgment: false
  - id: D2
    description: Mirrored assets, catalog availability, inventory integrity, and no-side-effect locale changes remain enforced.
    requirement: COVR-05
    verification:
      - kind: unit
        ref: python3 -m unittest discover -s tests -p 'test_*.py'
        status: pass
    human_judgment: false
status: complete
---

# Phase 2 Plan 02: Static Binding and Inventory Summary

**The mirrored admin shell now uses explicit static English bindings, localized metadata, and a source-level contract that verifies every declared binding in both bundled catalogs.**

## Accomplishments

- Bound static navigation, overview, controls, configuration labels, placeholders, login shell, close controls, and Dynmap metadata through `data-i18n*` attributes.
- Preserved raw commands, endpoints, IDs, configuration values, dialog state, polling, and dynamic renderer ownership.
- Added a compact static-binding contract to the Phase 1 inventory and regression checks for exact source literals, binding attributes, catalog coverage, and all mirrored assets.

## Task Commits

1. `ffbeb6f` — complete static shell bindings and mirrored inventory/runtime updates.
2. `542650f` — static binding, catalog, inventory, and parity regression gate.

## Verification

- Focused locale, inventory, and runtime tests — 14 passed.
- Full regression suite — 29 passed.
- Four Node syntax checks — passed.
- Five mirrored asset comparisons — passed.

## Deviations from Plan

**[Rule 2 - Missing Critical] Compact static-binding contract** — stored exact binding sources in `staticBindingContract` beside the Phase 1 dynamic-literal evidence, preserving staged Phase 3 catalog entries while making every Phase 2 binding fail closed.

**Total deviations:** 1 auto-fixed. **Impact:** Keeps literal-level static evidence executable without altering deferred dynamic renderer ownership.

## Issues Encountered

None.

## Next Phase Readiness

Phase 3 can localize stateful renderers from existing state while retaining the no-request/no-timer locale-switching boundary.

## Self-Check: PASSED
