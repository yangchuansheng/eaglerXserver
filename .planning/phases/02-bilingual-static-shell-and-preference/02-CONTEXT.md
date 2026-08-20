# Phase 2: Bilingual Static Shell and Preference - Context

**Gathered:** 2026-08-20
**Status:** Ready for planning
**Mode:** Generic-agent workaround; autonomous `--auto` decisions

<domain>
## Phase Boundary

Phase 2 wires the verified bundled locale runtime into the mirrored administration shell. It establishes English HTML first paint, a persistent header locale selector, explicit static DOM bindings, and localized document and accessibility metadata. The phase covers `PREF-01` through `PREF-04`, `COVR-01`, and `COVR-05`.

Phase 3 owns stateful renderer, dialog, toast, terminal-history, polling-display, and server-operation localization. Phase 4 owns release parity proof and full browser acceptance across both web roots.

</domain>

<decisions>
## Implementation Decisions

### Static shell wiring

- **D2-01:** Keep complete English source copy in `admin.html`, including static labels, navigation, headings, buttons, hints, initial empty states, form labels, and static accessibility metadata. English source remains usable when JavaScript or `admin-i18n.js` is unavailable.
- **D2-02:** Load `admin-i18n.js` before `admin.js` in both mirrored HTML documents. `admin.js` owns the small page-binding lifecycle: restore preference, populate the selector from the locale registry, apply static bindings, then begin existing administration initialization.
- **D2-03:** Use explicit semantic bindings beside their targets: `data-i18n` for text content, `data-i18n-title` for `title`, `data-i18n-placeholder` for `placeholder`, and `data-i18n-aria-label` for accessible names. Each binding stores a Phase 1 catalog key.
- **D2-04:** Preserve the existing DOM IDs, section order, class names, inline command tokens, endpoint paths, and administration event handlers. The current six admin assets remain byte-identical across `web-1.8` and `web-1.12` after every Phase 2 change.

### First-paint and initial locale selection

- **D2-05:** Set `<html lang="en">` and the English document title in source HTML. This supplies the deterministic first-visit English administration shell.
- **D2-06:** After the DOM is available and before `init()` performs its first status request, resolve the origin-scoped preference and synchronously apply a valid selected locale to static DOM targets. A saved `zh-CN` preference therefore takes effect before administration initialization begins.
- **D2-07:** Browser-language negotiation stays outside v1.0. The first visit always selects `en`.

### Header selector structure

- **D2-08:** Add a native `<select id="locale-select" name="locale">` to the existing always-visible `header-right` cluster, before the status and logout controls. Populate its options from `EaglerXI18n.locales` in registry order with values `en` and `zh-CN` and labels `English` and `简体中文`.
- **D2-09:** Associate the selector with a visible or visually-hidden `<label for="locale-select">` whose text uses an `accessibility.*` or `header.*` translation key. The select handles `change` through one listener that applies the selected locale in place.
- **D2-10:** Keep selector layout inside the existing header design: at least 38px height on desktop and 44px on the 520px mobile breakpoint, with header controls wrapping while the selector, status, and logout action remain reachable.

### Preference persistence and recovery

- **D2-11:** Use only `EaglerXI18n.PREFERENCE_KEY` (`eaglerx_admin_locale`) for locale persistence. Read, remove, and write `localStorage` through guarded `try/catch` helpers.
- **D2-12:** Accept stored values only when they match an own registered locale ID. Missing, malformed, stale, unavailable, and storage-blocked values resolve to `en`; a removable invalid stored value is cleared on a best-effort basis.
- **D2-13:** A valid selector change updates the runtime locale and static DOM immediately. A failed storage write keeps that valid selection for the current page session, so administration remains available with the chosen presentation.
- **D2-14:** Preference scope follows browser origin. The `:5200` and `:5201` administration origins retain independent locale choices through native Web Storage behavior.

### DOM metadata and accessibility coverage

- **D2-15:** Each locale application updates `document.documentElement.lang`, `document.title`, the selector label and options, static visible copy, `title`, `placeholder`, `aria-label`, and the Dynmap iframe `title` as one DOM-only operation.
- **D2-16:** Keep `aria-labelledby`, `for`, element IDs, command values, and URL values as structural or operational references. Translated text belongs on their referenced labels and elements.
- **D2-17:** Cover static header, skip link, navigation, hero, overview labels, section headings, card titles and notes, static control buttons, configuration labels and placeholders, login-shell labels, close-control accessible names, map iframe title, and static empty-state copy. Dynamic values inserted by existing renderers remain Phase 3 presentation ownership.

### State-preserving switching boundary

- **D2-18:** The locale-change handler performs only locale validation, preference persistence, selector synchronization, document metadata updates, and explicit static binding updates. It calls no API, sends no RCON command, starts no timer, and invokes no existing `init()` path.
- **D2-19:** Preserve `TOKEN`, session expiry, authentication modal state, form values, selections, focus, scroll position, `ACTION_DIALOG`, `WORLD_INFO_CACHE`, `CONFIG_CACHE`, `ONLINE_PLAYERS`, structure state, `REFRESH_IN_FLIGHT`, polling handles, queued refreshes, and raw terminal/server output during Phase 2 locale changes.
- **D2-20:** Phase 3 will re-render dynamic status, player, world, TPS, configuration, dialog, toast, and terminal presentation from existing semantic state. It will retain Phase 2's no-fetch/no-timer-switching boundary.

### the agent's Discretion

- Choose the smallest helper names and binding iteration implementation that follow the existing classic-browser JavaScript style.
- Choose exact Phase 1 message keys for each static target while preserving the inventory and catalog integrity checks.
- Choose compact selector CSS declarations that preserve current header breakpoints and focus treatment.
- Choose static test structure inside `tests/test_regressions.py` for English source coverage, binding-key validity, storage recovery, selector registry metadata, and mirrored assets.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and phase scope

- `AGENTS.md` — repository constraints, mirror model, language policy, and protected assets.
- `.planning/PROJECT.md` — product scope, fixed locale preference key, first-visit English policy, and state-preservation requirement.
- `.planning/ROADMAP.md` — Phase 2 goal, requirements, success criteria, and Phase 3/4 boundaries.
- `.planning/REQUIREMENTS.md` — `PREF-01` through `PREF-04`, `COVR-01`, and `COVR-05` acceptance requirements.
- `.planning/STATE.md` — current phase position and accumulated locale decisions.

### Phase 1 contract and evidence

- `.planning/phases/01-locale-contract-and-inventory/01-CONTEXT.md` — locked locale, fallback, raw-value, and mirror decisions.
- `.planning/phases/01-locale-contract-and-inventory/01-RESEARCH.md` — browser-native architecture and static binding guidance.
- `.planning/phases/01-locale-contract-and-inventory/01-UI-SPEC.md` — protected design baseline, selector placement, responsive dimensions, and state contract.
- `.planning/phases/01-locale-contract-and-inventory/01-VALIDATION.md` — existing standard-library verification paths.
- `.planning/phases/01-locale-contract-and-inventory/01-SECURITY.md` — locale-selection and DOM-sink trust boundaries.
- `.planning/phases/01-locale-contract-and-inventory/01-UAT.md` — completed Phase 1 checks and explicit Phase 2 handoff.
- `.planning/phases/01-locale-contract-and-inventory/01-VERIFICATION.md` — verified Phase 1 runtime/inventory contract and deferred page wiring.

### Research and implementation sources

- `.planning/research/ARCHITECTURE.md` — script order, selector lifecycle, and no-request locale application boundary.
- `.planning/research/STACK.md` — English source first paint, explicit `data-i18n*` attributes, native selector, and storage guidance.
- `.planning/research/PITFALLS.md` — storage recovery, metadata coverage, dynamic-state boundary, and mirror risks.
- `.planning/codebase/CONVENTIONS.md` — classic browser JavaScript and mirrored asset conventions.
- `.planning/codebase/STRUCTURE.md` — both web-root integration locations.
- `.planning/codebase/STACK.md` — dependency-free browser stack constraints.
- `web-1.8/admin.html` and `web-1.12/admin.html` — mirrored static shell, script order, accessible structure, and selector insertion point.
- `web-1.8/admin.js` and `web-1.12/admin.js` — initialization order, auth/session state, timers, caches, dialogs, and dynamic ownership boundaries.
- `web-1.8/admin.css` and `web-1.12/admin.css` — header cluster, focus, and responsive selector styling.
- `web-1.8/admin-i18n.js` and `web-1.12/admin-i18n.js` — verified locale registry, fallback, preference key, and translation runtime.

### External specifications

No external specification is required. Repository research carries the relevant browser-platform guidance.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `window.EaglerXI18n` already exposes `DEFAULT_LOCALE`, `PREFERENCE_KEY`, `locales`, `getLocale()`, `setLocale()`, and `t()` for the selector and static-binding lifecycle.
- `admin.js` already has one `init()` entry point and runs it after all static markup is parsed; it provides the smallest place to apply a stored locale before administration fetches begin.
- The header's `header-right` cluster, existing focus styling, and 1180px/820px/520px responsive rules provide the selector container and responsive behavior.
- Exact Phase 1 mirrors exist for `admin.html`, `admin.js`, `admin.css`, and `admin-i18n.js` across both web roots.

### Established Patterns

- Static source copy is authored in `admin.html`; dynamic presentation is produced by `admin.js` renderers and dialog helpers.
- `TOKEN`, caches, timers, refresh guards, dialog state, and raw console output are long-lived runtime state. Page reload or reinitialization would disrupt operational work.
- `sessionStorage` helpers already use guarded Web Storage calls; locale preference can follow the same guarded browser-native pattern while remaining separate from authentication storage.
- `textContent` and `escapeHtml()` define the existing safe DOM boundaries; static locale bindings use `textContent` and `setAttribute`.

### Integration Points

- Script order in `admin.html` connects the verified runtime with the existing page initialization.
- The header connects locale registry metadata, preference restoration, and the pre-authenticated shell.
- Explicit static bindings connect Phase 1 catalog keys to source HTML text and attribute targets.
- The locale-change handler connects static presentation updates while leaving existing runtime state holders untouched.

</code_context>

<specifics>
## Specific Ideas

- English source HTML delivers the reliable first paint and fallback shell.
- The header selector stays available before and after authentication.
- Native `localStorage` preserves a valid choice independently for ports 5200 and 5201.
- The selector updates the shell in place, with Phase 3 owning dynamic renderers and dialogs.
- Both web roots retain exact asset parity throughout the milestone.

</specifics>

<deferred>
## Deferred Ideas

- Stateful status, player, world, TPS, configuration, toast, dialog, terminal-history, and raw-output presentation localization belongs to Phase 3.
- UI-owned number and time formatting belongs to Phase 3.
- Full browser acceptance, computed accessible-name inspection, and release parity proof across both roots belong to Phase 4.
- Additional locale catalogs, browser-language negotiation, runtime catalog downloads, and server-output translation remain outside v1.0.

</deferred>

---

*Phase: 2-Bilingual Static Shell and Preference*
*Context gathered: 2026-08-20*
