# Project Research Summary

**Project:** EaglercraftX 1.8 Server
**Domain:** Dependency-free browser administration UI internationalization
**Researched:** 2026-08-20
**Confidence:** HIGH

## Executive Summary

EaglercraftX packages two Paper server versions with mirrored browser admin assets. Milestone v1.0 changes the operator-facing presentation layer: English becomes the complete first-visit language, while the management API, RCON command semantics, authentication, polling, and raw server responses retain their established behavior. Experts build this as a small browser-native i18n boundary: an English catalog, semantic keys, deterministic fallback, declarative HTML bindings, and renderer-level dynamic text.

Use a project-owned `admin-i18n.js` runtime loaded before the existing classic `admin.js`; retain English source copy in `admin.html`; add a native header selector backed by safe `localStorage`; and use `Intl` with the selected locale for UI-owned formatting. Keep every common admin asset byte-identical across `web-1.8` and `web-1.12`. The material delivery risks are incomplete dynamic-string coverage, stale UI after a live switch, unsafe interpolation, and mutation of Paper/plugin/RCON diagnostics. Solve them through a complete string inventory, semantic cached state, text-only raw-output paths, static catalog checks, mirror checks, and a state-based browser acceptance matrix.

## Key Findings

### Recommended Stack

The existing plain HTML/CSS/classic JavaScript stack fully covers v1. A flat English catalog and small global `AdminI18n` API fit one single-page interface and one complete locale; adding npm, a framework, a remote catalog, or a translation service would expand deployment and review scope without serving a v1 requirement.

**Core technologies:**

- HTML `lang` and explicit `data-i18n*` attributes: bind static text and accessible attributes while preserving an English first paint.
- Native `<select>` and `localStorage`: expose and persist an explicit locale preference with browser-native keyboard behavior.
- Flat project-owned message catalog with `t(key, params)`: supplies semantic keys, finite English fallback, and named plain-text interpolation.
- `Intl.NumberFormat` / `Intl.DateTimeFormat`: format UI-owned numbers and times from the active locale.
- Python `unittest`, `node --check`, and `cmp -s`: enforce key coverage, syntax, and mirrored-asset parity with existing tools.

### Expected Features

**Must have (table stakes):**

- Complete English baseline and deterministic `selected locale → English → visible marker` fallback.
- Header locale selector with validated, safe `localStorage` persistence; English is the sole v1 selectable catalog.
- Keyed coverage for static HTML, dynamic status, dialogs, toasts, validation, metadata, titles, placeholders, and ARIA names.
- State-preserving locale application; current token, inputs, selection, cached server state, focus, and pending dialog work survive a switch.
- Exact raw Paper/plugin/RCON output and stable command/configuration semantics.
- Byte-identical admin assets and catalog keys for 1.8 and 1.12.

**Should have (competitive):**

- Visible missing-key diagnostics and console de-duplication to expose catalog defects early.
- Locale-aware UI number/time formatting plus a compact automated catalog/mirror gate.

**Defer (v2+):**

- A second complete locale, RTL certification, pseudo-localization, ICU-scale grammar, remote catalog delivery, and translation-management integration.

### Architecture Approach

Add one browser presentation boundary and preserve all existing backend behavior. `admin.html` provides an English shell and declarative bindings; `admin-i18n.js` owns the registry, catalog, fallback, storage, document metadata, formatting, and locale-change notification; `admin.js` owns operational state and renders client-owned prose from semantic keys; API/RCON values remain opaque data rendered through text nodes.

**Major components:**

1. `admin-i18n.js` — English catalog, finite fallback, interpolation, registry, persistence, formatting, and `AdminI18n` API.
2. `admin.html` / `admin.css` — English-first static shell, locale selector, explicit bindings, and responsive selector styling.
3. `admin.js` renderers — map cached semantic state and dialog schemas to translated UI while retaining field values and focus.
4. Raw-output boundary — preserves API/RCON response bodies, protocol values, names, commands, coordinates, and diagnostics verbatim.
5. Regression guard — validates English-key authority and byte parity of all mirrored admin assets.

### Critical Pitfalls

1. **Incomplete string inventory** — inventory HTML attributes, inline handlers, all UI sinks, dialogs, errors, notifications, and timer paths before migration; machine-check English-key coverage.
2. **Fallback defects** — use exactly two catalog reads followed by a visible missing-key marker; English completeness is the release schema.
3. **Rendered strings stored as state** — retain state codes, keys, and interpolation data, then re-render from caches without network activity.
4. **Unsafe or altered operational data** — keep catalog values plain text; use `textContent` for raw values and preserve escaping at retained `innerHTML` sinks.
5. **Mirrored-tree or state-space gaps** — enforce asset equality and test logged-out, authenticated, error, dialog, storage, cached-data, and both-version states.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Locale Contract and Inventory

**Rationale:** Every later migration depends on a complete semantic key schema and predictable lookup contract.

**Delivers:** `admin-i18n.js` with complete English catalog, locale registry, bounded fallback, named interpolation, safe storage access, formatter helpers, and an audited inventory of static/dynamic message surfaces.

**Addresses:** English baseline, deterministic fallback, interpolation, future catalog extensibility, and stable command/display separation.

**Avoids:** Missed rarely visited strings, recursive fallback, blank controls, catalog HTML, and unsafe interpolation.

### Phase 2: English-First Static Shell and Preference

**Rationale:** The runtime contract can now safely drive first paint, selector behavior, and all static accessibility metadata before operational initialization.

**Delivers:** English `admin.html`, explicit `data-i18n*` bindings, header native selector, responsive styles, localized title/`lang`/ARIA/placeholder surfaces, and validated origin-local preference persistence.

**Uses:** Native `<select>`, `localStorage`, HTML language metadata, and the catalog DOM binder.

**Implements:** Static document shell and locale-selection component.

**Avoids:** language flash, inaccessible Chinese metadata, startup failure from storage errors, and confusion between ports 5200 and 5201 storage origins.

### Phase 3: Dynamic Renderers and Raw-Output Boundary

**Rationale:** Dynamic state and generic dialogs have the greatest migration surface and must consume the Phase 1 contract after static behavior is stable.

**Delivers:** Keyed status/auth/hero/toast/console wrappers, key-based action-dialog schemas, cache-only rerenders for world, Seed, structures, players, TPS, and config, plus active-locale number/time formatting.

**Addresses:** Dynamic, dialog, notification, live-switch, and locale-formatting requirements.

**Avoids:** stale mixed-language views, lost dialog input/focus, duplicate requests or timers, translated command values, and mutation of raw responses.

### Phase 4: Mirror Gate and Release Matrix

**Rationale:** Two shipped web roots and a large dynamic state space require release-level proof after all migrations land.

**Delivers:** Python regression checks for key references, English completeness, duplicate keys, managed legacy-string scan, and equality of `admin.html`, `admin.css`, `admin.js`, and `admin-i18n.js`; browser acceptance evidence for both Minecraft versions.

**Addresses:** Mirrored-version parity, fallback reliability, accessibility completeness, raw-output fidelity, and workflow preservation.

**Avoids:** one-version drift and screenshot-only completion that misses auth, error, cache, storage, dialog, and destructive-action states.

### Phase Ordering Rationale

- A validated English catalog is the schema for every static and dynamic binding, so it must precede UI conversion.
- Static shell and persistence establish safe early initialization; dynamic renderer conversion then reuses that stable API.
- The generic dialog and cached-renderer work belongs together because both require semantic state to enable side-effect-free live application.
- Final verification collects the shared parity and full-state checks, preventing late drift across the two runtime-selected trees.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 3:** inspect every current renderer, dialog, timer, cache, and `innerHTML` sink to choose the smallest semantic-state conversion that preserves inputs and raw data.
- **Phase 4:** plan an executable browser matrix for both served origins and both Minecraft versions; the repository has limited existing browser automation.

Phases with standard patterns (skip research-phase):

- **Phase 1:** native catalog, finite fallback, named interpolation, and safe Web Storage are well documented.
- **Phase 2:** semantic `data-*` bindings, native select controls, document language, and ARIA attribute updates are established browser patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Native browser APIs match the plain classic-script deployment and official standards support the selected capabilities. |
| Features | MEDIUM | Codebase requirements and accessibility behavior are clear; operator preference evidence lacks interviews and analytics. |
| Architecture | HIGH | Component boundaries derive directly from existing admin assets, caches, raw RCON flow, and mirror topology. |
| Pitfalls | HIGH | Risks are evidenced by current rendering paths, storage semantics, accessibility guidance, and mirrored deployment behavior. |

**Overall confidence:** HIGH

### Gaps to Address

- **Browser support floor:** validate the oldest actual operator browser or launcher environment before relying on any newer syntax beyond the current `admin.js` baseline.
- **Historical client-log policy:** define whether existing browser-owned console entries retain their original locale; research recommends retaining prior entries for operational stability.
- **Future-language ownership:** choose terminology review ownership before adding the first non-English complete catalog.
- **Origin expectation:** document that port 5200 and 5201 maintain separate browser-local locale preferences and test both surfaces.

## Sources

### Primary (HIGH confidence)

- [STACK.md](./STACK.md) — native stack, compatibility, catalog contract, and verification gates.
- [ARCHITECTURE.md](./ARCHITECTURE.md) — current rendering paths, component boundaries, data flow, and build order.
- [PITFALLS.md](./PITFALLS.md) — failure modes, security boundaries, phase exits, and release matrix.
- [WHATWG HTML](https://html.spec.whatwg.org/multipage/dom.html#the-lang-and-xml:lang-attributes) — language metadata and Web Storage model.
- [ECMA-402](https://tc39.es/ecma402/) — locale-aware browser formatting.
- [W3C WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html) and [WAI-ARIA](https://www.w3.org/TR/wai-aria-1.2/#aria-label) — language and accessible-name requirements.

### Secondary (MEDIUM confidence)

- [FEATURES.md](./FEATURES.md) — operator-facing feature prioritization and explicit v1 exclusions.
- [MDN Web Storage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) — origin scoping and storage failure behavior.
- [MDN `textContent`](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent) and [MDN `innerHTML`](https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML) — safe text insertion and injection-sink guidance.

---
*Research completed: 2026-08-20*
*Ready for roadmap: yes*
