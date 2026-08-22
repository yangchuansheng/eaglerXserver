# Phase 3: Dynamic Renderers and Raw-Output Boundary - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents. Decisions are captured in `03-CONTEXT.md`; this log preserves the autonomous alternatives considered.

**Date:** 2026-08-21
**Phase:** 3-dynamic-renderers-and-raw-output-boundary
**Mode:** Autonomous `--auto`; automatic plan chaining was suppressed because this task is restricted to the discussion stage.
**Areas discussed:** dynamic renderer state, dialogs and feedback, raw operational output, locale-change continuity, mirror and test boundary

---

## Dynamic renderer state

| Option | Description | Selected |
|--------|-------------|----------|
| Existing catalog keys with semantic state descriptors | Render client-owned auth, status, player, world, TPS, and config copy from the existing bilingual contract and cached raw data. | ✓ |
| Keep source literals in renderers | Continue rendering stateful text directly from source strings. | |
| Global DOM text replacement | Discover and replace dynamic text through document-wide scanning. | |

**User's choice:** `[auto]` Recommended default selected: existing catalog keys with semantic state descriptors.
**Notes:** Existing caches and state holders provide the smallest reliable locale-refresh source. Composed keys are limited to semantic interpolated messages.

## Dialogs and feedback

| Option | Description | Selected |
|--------|-------------|----------|
| In-place dialog and feedback refresh | Localize titles, descriptions, fields, placeholders, validation, actions, toasts, and client logs while retaining the active interaction state. | ✓ |
| Close active dialogs | End the current interaction during locale changes. | |
| Reopen with defaults | Recreate dialogs after switching locale and discard entered values. | |

**User's choice:** `[auto]` Recommended default selected: in-place dialog and feedback refresh.
**Notes:** Dialog identity, values, selected options, focus, selection range, command preview, and action callbacks remain stable. Toast expiry continues through locale refresh.

## Raw operational output

| Option | Description | Selected |
|--------|-------------|----------|
| Opaque raw payload with localized framing | Keep server payload strings intact and translate only client-owned labels, prefixes, empty-output wrappers, and errors around them. | ✓ |
| Translate response text | Convert Paper/plugin/RCON output through locale catalogs. | |
| Normalize response text | Trim, parse, or rewrite output before rendering. | |

**User's choice:** `[auto]` Recommended default selected: opaque raw payload with localized framing.
**Notes:** Console history separates keyed client entries from raw operational entries. English client logs use concise sentence case; raw values retain their source wording.

## Locale-change continuity

| Option | Description | Selected |
|--------|-------------|----------|
| Synchronous existing-state rerender | Refresh localized DOM from current state without requests, RCON commands, polling restarts, or timer creation. | ✓ |
| Refetch dashboard data | Reload stateful data after every locale change. | |
| Restart initialization and polling | Run the authentication and polling lifecycle again. | |

**User's choice:** `[auto]` Recommended default selected: synchronous existing-state rerender.
**Notes:** Request guards, polling handles, queued refreshes, restart recovery timers, authentication, raw console history, and in-flight work retain their existing owners.

## Mirror and test boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Exact mirrors plus focused Phase 3 tests | Keep all five paired admin assets byte-identical and test dynamic rendering, raw boundaries, `Intl`, and lifecycle behavior. | ✓ |
| Independent web-root implementations | Let each supported client tree evolve locale behavior independently. | |
| Defer all validation | Leave dynamic contract coverage until release work. | |

**User's choice:** `[auto]` Recommended default selected: exact mirrors plus focused Phase 3 tests.
**Notes:** Phase 4 retains served-browser and release-matrix acceptance. Phase 3 preserves the existing visual redesign and uses standard-library checks.

## the agent's Discretion

- Minimal descriptor and helper shapes for client entries, active toast state, and locale rerendering.
- Exact composed-key names, English/`zh-CN` wording, and focused Node VM/Python tests.
- DOM-level implementation details that retain current accessibility and responsive behavior.

## Deferred Ideas

- Full served-browser acceptance and release parity proof belong to Phase 4.
- Additional locales, runtime catalog delivery, browser-language negotiation, and server-side output translation remain outside v1.0.
