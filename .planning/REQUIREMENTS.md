# Requirements: EaglercraftX 1.8 Server

**Defined:** 2026-08-20
**Core Value:** Operators can reliably administer either supported server version through one browser-based control plane.

## v1 Requirements

Requirements for milestone v1.0 Admin i18n.

### i18n Core

- [ ] **CORE-01**: The admin interface provides a complete English catalog for all client-authored interface text.
- [ ] **CORE-02**: Translation lookup falls back from the active locale to English and then to a visible missing-key marker.
- [ ] **CORE-03**: The translation API supports named parameter interpolation and renders catalog values as safe plain text.
- [ ] **CORE-04**: The locale registry supports adding future bundled locale catalogs without changing selector or renderer contracts.
- [ ] **CORE-05**: Missing translation keys produce a visible diagnostic marker and a deduplicated console diagnostic.

### Locale Preference

- [ ] **PREF-01**: The admin interface displays English on first visit.
- [ ] **PREF-02**: The header provides a native locale selector populated from the bundled locale registry.
- [ ] **PREF-03**: A valid locale selection persists across browser sessions through `localStorage`.
- [ ] **PREF-04**: Missing, invalid, stale, or inaccessible locale preferences recover safely to English.

### Translation Coverage

- [ ] **COVR-01**: Static headings, labels, buttons, hints, empty states, and navigation use translation keys.
- [ ] **COVR-02**: Dynamic authentication, status, player, world, TPS, and configuration messages use translation keys.
- [ ] **COVR-03**: Dialog titles, descriptions, fields, placeholders, validation messages, and actions use translation keys.
- [ ] **COVR-04**: Toasts, loading states, success messages, warnings, and client-authored errors use translation keys.
- [ ] **COVR-05**: The document language, page title, element titles, iframe title, form labels, and ARIA text update with the active locale.
- [ ] **COVR-06**: UI-owned numbers and dates use native `Intl` formatting with the active locale.

### Operational Safety

- [ ] **SAFE-01**: Changing locale preserves authentication, entered values, selections, focus, dialogs, and cached server state.
- [ ] **SAFE-02**: Paper, plugin, and RCON response content remains byte-for-byte unchanged in the admin interface.
- [ ] **SAFE-03**: Command arguments, configuration enums, and protocol values remain independent from translated display labels.
- [ ] **SAFE-04**: Locale changes re-render from existing client state while preserving request, polling, and server-operation state.

### Mirrored-Version Parity

- [ ] **PARI-01**: `web-1.8` and `web-1.12` use identical locale identifiers, catalog keys, fallback behavior, and locale interactions.
- [ ] **PARI-02**: Automated checks verify English-key coverage, referenced-key integrity, and equality of mirrored admin assets.
- [ ] **PARI-03**: Browser acceptance covers authentication, player, world, configuration, dialog, notification, command, and error flows for both web versions.

## v2 Requirements

Deferred until the English-first foundation is verified.

### Additional Locale Support

- **LOCALE-01**: The admin interface provides a second complete human-language catalog.
- **LOCALE-02**: The project provides pseudo-locale and text-expansion checks for catalog review.
- **LOCALE-03**: The translation runtime supports advanced plural and grammatical selection when a maintained locale requires it.

### Extended Localization Infrastructure

- **LOCALE-04**: The admin interface supports certified RTL layout for a committed RTL locale.
- **LOCALE-05**: Locale catalogs can be delivered independently through a versioned release process.
- **LOCALE-06**: Translation management integrates with a maintained localization workflow.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Translation of Paper, plugin, or RCON output | Server-originated text is open-ended operational evidence and must retain exact source wording. |
| Browser-language auto-selection | Deterministic English first load supports predictable operation and troubleshooting. |
| Runtime-downloaded catalogs | Bundled catalogs avoid availability, cache, version-skew, and integrity dependencies. |
| Runtime machine translation | Administrative terminology requires stable, reviewed wording. |
| Global DOM text replacement | Explicit semantic keys provide reliable coverage for text, attributes, and dynamic renderers. |
| Broad modal or visual redesign | Existing administration behavior remains the product baseline for this localization milestone. |
| Translation of command tokens or configuration values | Stable protocol values protect command correctness and server behavior. |

## Traceability

Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Pending | Pending |
| CORE-02 | Pending | Pending |
| CORE-03 | Pending | Pending |
| CORE-04 | Pending | Pending |
| CORE-05 | Pending | Pending |
| PREF-01 | Pending | Pending |
| PREF-02 | Pending | Pending |
| PREF-03 | Pending | Pending |
| PREF-04 | Pending | Pending |
| COVR-01 | Pending | Pending |
| COVR-02 | Pending | Pending |
| COVR-03 | Pending | Pending |
| COVR-04 | Pending | Pending |
| COVR-05 | Pending | Pending |
| COVR-06 | Pending | Pending |
| SAFE-01 | Pending | Pending |
| SAFE-02 | Pending | Pending |
| SAFE-03 | Pending | Pending |
| SAFE-04 | Pending | Pending |
| PARI-01 | Pending | Pending |
| PARI-02 | Pending | Pending |
| PARI-03 | Pending | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 0
- Unmapped: 22

---
*Requirements defined: 2026-08-20*
*Last updated: 2026-08-20 after requirement confirmation*
