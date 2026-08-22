---
phase: 02-bilingual-static-shell-and-preference
plan: "01"
subsystem: i18n
tags: [i18n, preference, static-shell, regression]
requires:
  - phase: 01-locale-contract-and-inventory
    provides: bundled locale registry and fallback runtime
provides:
  - English-first shell and native locale selector
  - Guarded origin-scoped locale preference lifecycle
  - DOM-only locale application with responsive selector styling
affects: [phase-2-static-shell, phase-3-dynamic-renderers, phase-4-mirror-gate]
actuals:
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [guarded-localStorage, explicit-dom-bindings, mirrored-admin-assets]
key-files:
  created: [.planning/phases/02-bilingual-static-shell-and-preference/02-01-SUMMARY.md]
  modified: [web-1.8/admin.html, web-1.8/admin.js, web-1.8/admin.css, web-1.8/admin-i18n.js, tests/test_regressions.py]
key-decisions:
  - "Locale changes update only explicit static DOM bindings and metadata."
  - "A failed localStorage write retains the selected locale for the current session."
requirements-completed: [PREF-01, PREF-02, PREF-03, PREF-04, COVR-05]
coverage:
  - id: D1
    description: English first paint and the native locale selector precede administration initialization.
    requirement: PREF-01
    verification:
      - kind: unit
        ref: tests/test_regressions.py#StaticShellLocaleTests
        status: pass
    human_judgment: false
  - id: D2
    description: Preference recovery and selector changes preserve operational state by staying within the DOM-only lifecycle.
    requirement: PREF-04
    verification:
      - kind: unit
        ref: tests/test_regressions.py#StaticShellLocaleTests.test_locale_recovery_and_current_session_write_failure
        status: pass
    human_judgment: false
status: complete
---

# Phase 2 Plan 01: English-First Locale Preference Summary

**English first paint, a guarded native language selector, and a DOM-only locale lifecycle now run before the first administration request.**

## Accomplishments

- Added the labelled `#locale-select`, English source metadata, runtime script order, and responsive 38px/44px selector treatment.
- Restored only registered locale IDs from `eaglerx_admin_locale`, cleared invalid stored values best-effort, and retained valid session selection after write failure.
- Added focused standard-library and Node VM regression coverage for lifecycle safety and mirrored assets.

## Task Commits

1. `c767ac8` — locale preference lifecycle.
2. `e1e51f6` — selector styling and regression coverage.
3. `88bb4a6` — locale runtime script-order correction.

## Verification

- `python3 -m unittest tests.test_regressions.StaticShellLocaleTests -v` — passed.
- `node --check web-1.8/admin.js && node --check web-1.12/admin.js` — passed.
- Mirrored HTML, JavaScript, and CSS comparisons — passed.

## Deviations from Plan

**[Rule 2 - Missing Critical] Runtime catalog keys for selector and iframe metadata** — added `header.localeLabel` and `accessibility.dynmapFrame` in both mirrored catalogs so declared bindings always resolve.

**[Rule 1 - Bug] Runtime script URL correction** — loaded `admin-i18n.js` before the versioned `admin.js` URL after the focused source check exposed the missed script-order pattern.

**Total deviations:** 2 auto-fixed. **Impact:** Required for working selector and metadata bindings.

## Issues Encountered

None.

## Next Phase Readiness

Plan 02 can extend the established DOM-only lifecycle across the complete static shell.

## Self-Check: PASSED
