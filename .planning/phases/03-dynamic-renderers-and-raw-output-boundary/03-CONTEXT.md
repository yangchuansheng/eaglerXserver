# Phase 3: Dynamic Renderers and Raw-Output Boundary - Context

**Gathered:** 2026-08-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 localizes every stateful, client-authored administration surface: authentication and connection state, player and TPS renderers, world and structure status, configuration feedback, action dialogs, toasts, and client-owned console framing. It keeps the protected visual redesign, the active authenticated session, operator-entered values, cached server state, request guards, polling handles, and server-operation state intact. Paper, plugin, RCON, Dynmap, command, configuration, protocol, and player data retain their raw operational representation.

</domain>

<decisions>
## Implementation Decisions

### Dynamic renderer migration

- **D3-01:** Migrate authentication, status, player, world, TPS, seed/structure, runtime-toggle, and configuration renderers to translation calls backed by the existing Phase 1 inventory and bilingual catalogs. Keep the current `admin-i18n-inventory.json` source-to-key contract authoritative; add only focused composed-message keys where interpolation expresses one semantic sentence more clearly than concatenated literal fragments. — **Reversibility:** costly — renderer and catalog behavior share one exact key contract across both shipped web roots.
- **D3-02:** Store semantic presentation state rather than localized rendered strings. Existing raw state holders (`TOKEN`, `SERVER_INFO`, `WORLD_INFO_CACHE`, `CONFIG_CACHE`, `ONLINE_PLAYERS`, `WORLD_SEED`, `STRUCTURE_QUERY`, `LAST_STRUCTURE_RESULT`, and `LAST_STRUCTURE_CONTEXT`) remain the source for synchronous dynamic rerendering. Derived client wording is regenerated through `EaglerXI18n.t(key, params)`.
- **D3-03:** Format UI-owned numbers and dates/times through native `Intl` using the active `EaglerXI18n` locale. This includes dashboard counts, distances, structure totals, UI timestamps, and display-only TPS precision. Keep Minecraft tick values, command arguments, coordinates, seeds, version identifiers, player names, configuration values, and raw API/RCON payloads as raw operational data. Use a fixed 24-hour display policy for derived Minecraft clock time.

### Dialogs, fields, and validation

- **D3-04:** Make every client-authored action-dialog kicker, title, description, confirm/cancel action, field label, hint, placeholder, suggestion/empty text, preview framing, and validation message locale-key driven. Field defaults that are command tokens or operational examples (`Steve`, `minecraft:stone`, `true / false`, coordinates, NBT, enum values, and raw command previews) stay verbatim.
- **D3-05:** Locale changes refresh an open login or action dialog in place. Preserve the open dialog identity, entered field values, selected datalist value, `required`/min/max constraints, danger styling, preview command, focused field, and selection range; focus returns to the same field after labels and descriptions update. Dialog submit and cancel callbacks retain their existing command and authentication behavior.
- **D3-06:** Client validation uses keyed messages with named plain-text parameters, including the required-field message. Server and bridge errors remain raw values appended to keyed client context, so the interface never treats backend text as a translation key or catalog markup.

### Toasts, console framing, and raw operational output

- **D3-07:** Localize loading, success, warning, client-error, unavailable, and authentication toasts. Keep one toast lifecycle with its existing visibility and expiry timer; retain a small descriptor for the active client-authored toast so a locale refresh updates text without resetting the remaining timeout.
- **D3-08:** Represent console history as structured entries: a client entry carries a translation key and named raw parameters; an operational entry carries the exact payload string. UI-owned timestamp formatting and client prefixes use the active locale. RCON command text, raw Paper/plugin/RCON/Dynmap responses, backend error values, player values, configuration values, and command previews render as opaque text values. The browser performs no translation, trimming, parsing-for-display, normalization, escaping rewrite, or interpolation on the raw payload before insertion through the existing safe text sink. A client-authored prefix may surround or precede a raw payload as a separately rendered node.
- **D3-09:** Use concise English sentence-case client logs in the `en` catalog, with the operation first and raw diagnostic detail after a stable separator. Examples: `Configuration updated: {key} [{value}]` and `Request failed: {error}`. The `zh-CN` catalog supplies the corresponding operator-facing wording; raw values preserve their source spelling and content.

### Locale-change continuity and request ownership

- **D3-10:** Extend the existing locale selector path with one synchronous `rerenderLocalizedState()` step after static bindings apply. It renders from the current semantic state and DOM interaction snapshot only. It calls no `init()`, `fetch`, RCON command, API wrapper, `setInterval`, `setTimeout`, polling starter, or server-operation callback.
- **D3-11:** Preserve `PLAYERS_TIMER`, `TPS_TIMER`, `WORLD_INFO_TIMER`, `HERO_PULSE_TIMER`, `WORLD_INFO_REFRESH_HANDLE`, `RUNTIME_REFRESH_HANDLE`, `REFRESH_IN_FLIGHT`, `INITIAL_REFRESHING`, pending toggle state, restart recovery timers, and queued refresh semantics across locale changes. Existing `beginRefresh()` guards and timer handles remain the sole owners of requests and timer creation. — **Reversibility:** costly — these guards protect all authenticated dashboard refresh paths from duplicated server work.
- **D3-12:** Preserve authentication tokens and expiry, login/action dialog state, every visible form value, checkbox/radio/select choice, focus and selection range, cached panel data, raw console history, active toast lifecycle, and server-operation status. A locale update uses current data even while a request is in flight; the normal completion renderer applies the active locale when that request resolves.

### Mirror parity and verification boundary

- **D3-13:** Keep `web-1.8` and `web-1.12` byte-identical for `admin.html`, `admin.js`, `admin.css`, `admin-i18n.js`, and `admin-i18n-inventory.json` after every Phase 3 change. Maintain one locale ID set, catalog key set, fallback behavior, raw-output boundary, and locale-switch lifecycle. — **Reversibility:** costly — drift would create version-specific operator behavior inside one Docker image.
- **D3-14:** Add focused Phase 3 regression coverage in `tests/test_regressions.py` for dynamic key use, native `Intl` locale selection, dialog/toast/console state rerendering, raw payload preservation, locale-switch no-fetch/no-timer behavior, and byte-equal mirrors. Phase 4 owns served-browser acceptance and release-matrix proof across both web roots.

### the agent's Discretion

- Choose the smallest descriptor shapes and helper names that match the existing classic-browser JavaScript style.
- Choose composed-key names and exact English/`zh-CN` wording while retaining the Phase 1 inventory contract and the English-first fallback.
- Choose the smallest focused Node VM and Python `unittest` probes that demonstrate the required dynamic lifecycle without a browser framework.
- Preserve the current DOM structure, CSS visual redesign, responsive rules, motion behavior, and accessibility treatment.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product, scope, and repository constraints

- `AGENTS.md` — mirror model, language policy, protected visual baseline, API/RCON behavior, and version constraints.
- `.planning/PROJECT.md` — bilingual milestone scope, English default/fallback, presentation-only locale switching, raw-output boundary, and persisted preference key.
- `.planning/REQUIREMENTS.md` — Phase 3 requirements `COVR-02`, `COVR-03`, `COVR-04`, `COVR-06`, `SAFE-01`, `SAFE-02`, and `SAFE-04`.
- `.planning/ROADMAP.md` — fixed Phase 3 goal, success criteria, and Phase 4 release-validation boundary.
- `.planning/STATE.md` — current GSD session position and accumulated project decisions.

### Prior phase decisions and evidence

- `.planning/phases/01-locale-contract-and-inventory/01-CONTEXT.md` — locked catalog, fallback, interpolation, raw-value, and mirror decisions.
- `.planning/phases/01-locale-contract-and-inventory/01-RESEARCH.md` — browser-native renderer and raw-output guidance.
- `.planning/phases/01-locale-contract-and-inventory/01-SECURITY.md` — safe text/HTML sink and operational-value trust boundaries.
- `.planning/phases/01-locale-contract-and-inventory/01-VALIDATION.md` — standard-library validation strategy and later state-preservation handoff.
- `.planning/phases/01-locale-contract-and-inventory/01-UAT.md` — confirmed Phase 1 behavior and deferred UI migration boundary.
- `.planning/phases/01-locale-contract-and-inventory/01-VERIFICATION.md` — literal-level inventory, catalog parity, and raw-boundary evidence.
- `.planning/phases/02-bilingual-static-shell-and-preference/02-CONTEXT.md` — no-fetch/no-timer locale-switch boundary and preserved state holders.
- `.planning/phases/02-bilingual-static-shell-and-preference/02-UI-SPEC.md` — protected selector placement, accessibility bindings, and responsive baseline.
- `.planning/phases/02-bilingual-static-shell-and-preference/02-UAT.md` — Phase 2 lifecycle proof and Phase 3 handoff.
- `.planning/phases/02-bilingual-static-shell-and-preference/02-VERIFICATION.md` — verified selector lifecycle, static coverage, and current exact mirrors.

### Code and test integration

- `.planning/codebase/CONVENTIONS.md` — classic-browser JavaScript, console/toast patterns, and mirror conventions.
- `.planning/codebase/STRUCTURE.md` — paired web-root locations and test entry point.
- `.planning/codebase/STACK.md` — dependency-free browser stack and native `Intl`/Web Storage availability.
- `web-1.8/admin.html` — static shell, dialog DOM, console/toast nodes, script order, and protected visual structure.
- `web-1.8/admin.js` — dynamic state holders, renderers, auth flow, dialogs, console/toast functions, polling, request guards, and locale selector path.
- `web-1.8/admin.css` — protected dialog, toast, console, focus, responsive, and visual redesign treatment.
- `web-1.8/admin-i18n.js` — bundled registry, active-locale lookup, English fallback, plain-text interpolation, and existing catalogs.
- `web-1.8/admin-i18n-inventory.json` — exact dynamic source surfaces, presentation keys, and catalog-free operational records.
- `web-1.12/admin.html` — byte-identical Phase 3 mirror target.
- `web-1.12/admin.js` — byte-identical Phase 3 mirror target.
- `web-1.12/admin.css` — byte-identical Phase 3 mirror target.
- `web-1.12/admin-i18n.js` — byte-identical Phase 3 mirror target.
- `web-1.12/admin-i18n-inventory.json` — byte-identical Phase 3 mirror target.
- `script/http_server.py` — raw `response`, `error`, and `message` API payload sources plus structured world/runtime data.
- `tests/test_regressions.py` — existing static locale, inventory, runtime, raw-sink, and mirror regression patterns.

### External specifications

No external specifications are required. Repository contracts and native browser APIs define this phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `window.EaglerXI18n.t(key, params)`, `getLocale()`, and `setLocale()` already provide active-locale lookup, English fallback, missing-key diagnostics, and safe plain-text interpolation.
- `applyStaticLocale()` and its selector `change` listener provide the only allowed locale-change entry point; Phase 3 can append synchronous dynamic rerendering there.
- `WORLD_INFO_CACHE`, `CONFIG_CACHE`, `ONLINE_PLAYERS`, `SERVER_INFO`, `WORLD_SEED`, structure state, `ACTION_DIALOG`, `TOKEN`, and refresh handles already retain the data needed for in-place rendering.
- `log()` uses `textContent` for plain terminal text; `escapeHtml()` protects the existing structured `innerHTML` renderers.
- `beginRefresh()`/`endRefresh()`, `queueWorldInfoRefresh()`, `queueRuntimeRefresh()`, `startAutoRefresh()`, and `runInitialDashboardRefreshes()` centralize request and timer ownership.

### Established Patterns

- Client text currently lives in renderer branches, dialog config objects, toast/log calls, and state setters; raw RCON/API values arrive separately as `d.response`, `d.error`, `d.message`, and structured fields.
- Dialog fields keep operational command inputs and previews separate from labels and descriptions. `buildCommandParts()` and command builders already preserve raw command tokens.
- `formatNumber()` currently hard-codes `zh-CN`; console timestamps rely on the browser default locale. These are the direct native-`Intl` migration seams.
- Both web roots are currently byte-identical for all five Phase 3 administration assets; existing regressions already compare mirrors.

### Integration Points

- `setStatus()`, `startHeroPulse()`, `resetAuthUi()`, `renderWorldInfo()`, `refreshPlayers()`, `refreshTPS()`, `refreshConfig()`, `refreshRuntimeToggles()`, and structure renderers consume cached state and client-owned wording.
- `showActionDialog()`, `renderActionFields()`, `submitActionDialog()`, `showModal()`, and `openLoginModal()` own open-dialog presentation, field values, validation, and focus.
- `toast()` and `log()` provide the single feedback and console output sinks.
- `send()` owns RCON command framing and raw `d.response` insertion; `script/http_server.py` returns raw payloads in `response`, `error`, and `message` fields.

</code_context>

<specifics>
## Specific Ideas

- Preserve raw payload evidence exactly while localizing the surrounding operator-facing explanation.
- Preserve live administration context during a language switch, including focused input and an open destructive confirmation dialog.
- Use native `Intl` for presentation numbers and times, with raw operational values left unchanged.
- Keep client-authored English logs concise and sentence case.
- Keep the two web roots exact mirrors through focused Phase 3 checks; Phase 4 proves served-browser release behavior.

</specifics>

<deferred>
## Deferred Ideas

- Served-browser acceptance, cross-version release-matrix proof, and end-to-end user flows belong to Phase 4.
- Additional locale catalogs, browser-language negotiation, runtime catalog delivery, and server-side translation remain outside v1.0.
- Any new administration capability, API route, command, data source, or visual redesign remains outside Phase 3.

</deferred>

---

*Phase: 3-Dynamic Renderers and Raw-Output Boundary*
*Context gathered: 2026-08-21*
