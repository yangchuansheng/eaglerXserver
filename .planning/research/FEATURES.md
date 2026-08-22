# Feature Research: Admin Interface Internationalization

**Project:** EaglercraftX 1.8 Server admin plane  
**Milestone:** v1.0 Admin i18n  
**Research type:** Project Research — Features  
**Researched:** 2026-08-20  
**Overall confidence:** MEDIUM

## Research Framing

This milestone establishes a reliable localization contract for the existing browser admin interface. English is the only complete v1 locale. The design must support future bundled catalogs while preserving the exact operational data returned by Paper, plugins, and RCON.

The current surface is substantial: each version has a 243-line `admin.html` and a 2,205-line `admin.js`, with static labels plus authentication, status, player, world, TPS, configuration, dialog, toast, command, and failure-path text. The 1.8 and 1.12 admin HTML and JavaScript assets are currently byte-identical, so mirrored behavior is an existing invariant worth protecting.

Confidence is HIGH for repository observations and standards-backed accessibility behavior. Confidence is MEDIUM for operator preference judgments because this project has no recorded user interviews or usage analytics.

## Feature Landscape

### Table Stakes

| Feature | Expected operator behavior | Codebase-specific recommendation | Complexity | Confidence |
|---|---|---|---|---|
| Complete English baseline | Every admin control and client-authored message is understandable on first load. | Make English the source HTML language and the complete catalog. This avoids an initial-language flash and gives every key a canonical value. | Medium | HIGH |
| Deterministic fallback | Missing or invalid locale data still produces usable text. | Resolve `selected locale -> English -> visible diagnostic key`. Empty labels are unacceptable for destructive or operational controls. | Medium | HIGH |
| Header locale selector | Language choice is visible, predictable, and available before operators enter a workflow. | Use a native `<select>` in the header. List only bundled, complete locales; v1 therefore presents English as its single option. | Low | HIGH |
| Persistent preference | A returning operator sees the previously selected valid locale. | Store a stable locale code such as `en` in `localStorage`. Recover to English for absent, unavailable, malformed, or inaccessible storage values. | Low | HIGH |
| State-preserving live switch | Changing language updates the interface immediately without interrupting administration. | Re-render client-authored text in place while retaining the auth token, modal input, command input, selected player, current panel, and fetched server state. | Medium | MEDIUM |
| Static HTML coverage | Headings, sections, labels, buttons, hints, empty states, placeholders, and navigation all follow the selected locale. | Give translatable nodes stable keys or bindings. Keep English text in HTML as the pre-script and failure-safe baseline. | Medium | HIGH |
| Dynamic JavaScript coverage | Text created after load uses the active locale consistently. | Route status badges, loading states, player/world/config summaries, TPS labels, validation, API failures, and client log lines through one translation function. | High | HIGH |
| Interpolation and count handling | Names, values, durations, and counts appear in grammatical templates. | Use named parameters and locale-owned templates. Use `Intl.NumberFormat` for locale-sensitive counts and numeric UI values. Keep the v1 plural model small and explicit. | Medium | HIGH |
| Dialog localization | Every modal title, explanation, field label, placeholder, validation message, and action is localized as one coherent flow. | Pass stable message keys and semantic values into the existing dialog helpers. Localize accessible dialog names alongside visible headings. | Medium | HIGH |
| Toast and status localization | Success, warning, and failure messages are understandable and announced without moving focus. | Localize client-authored notification wrappers and expose suitable status/alert semantics. Keep embedded server details verbatim. | Medium | HIGH |
| Document metadata | Browser tabs and assistive technology identify the current interface language. | Update `<html lang>`, `<title>`/`document.title`, element `title`, and iframe `title` whenever locale changes. | Low | HIGH |
| Accessible names | Icon-only and compact controls retain meaningful names in every locale. | Include `aria-label`, `aria-labelledby` source text, form labels, and relevant descriptions in the catalog coverage inventory. | Medium | HIGH |
| Stable command semantics | Localization never changes the command or configuration value sent to the server. | Keep semantic values such as `survival`, `difficulty=2`, player names, and command text separate from translated display labels. | Medium | HIGH |
| Raw operational output fidelity | Operators can copy, search, compare, and troubleshoot exact server responses. | Preserve Paper/plugin/RCON output, `d.response`, version strings, player names, seeds, MOTD, commands, and property keys verbatim. Localize only client-authored framing around those values. | Medium | HIGH |
| Mirrored-version parity | The 1.8 and 1.12 admin planes expose the same keys, labels, fallback rules, and interactions. | Treat catalog key parity and byte-equivalent shared admin assets as release criteria. Add an automated comparison to the existing verification workflow. | Medium | HIGH |

### Useful Differentiators

| Feature | Operator value | Recommendation | Complexity | Confidence |
|---|---|---|---|---|
| English-first rendering | The interface is readable before JavaScript initialization and under partial script failure. | Keep human-readable English in the HTML baseline and bind it to catalog keys during startup. | Medium | HIGH |
| Locale switch with zero workflow loss | Operators can inspect terminology without re-authenticating or re-entering commands. | Separate state from rendered labels; refresh text nodes and attributes without rebuilding operational state. | Medium | MEDIUM |
| Explicit UI/output boundary | Diagnostic evidence remains exact while navigation and action feedback become localizable. | Classify every string source as catalog text, semantic value, or raw server value. Apply this classification at rendering boundaries. | Medium | HIGH |
| Visible fallback diagnostics | Development and parity errors are discoverable before release. | Render a recognizable key marker after both selected-locale and English lookup fail; optionally report the missing key in the browser console. | Low | MEDIUM |
| Automated mirror gate | A change cannot silently localize one supported game version only. | Compare `admin.html`, `admin.js`, locale catalogs, and relevant CSS across `web-1.8` and `web-1.12` in a repeatable check. | Low | HIGH |
| Coverage inventory by text surface | Reviewers can verify localization beyond obvious button labels. | Track static text, dynamic text, attributes, dialogs, notifications, metadata, and accessibility strings as explicit acceptance groups. | Low | HIGH |

### Anti-Features

These choices expand risk or blur the operational contract, so they belong outside v1.

| Excluded feature | Why it harms this milestone | Revisit trigger |
|---|---|---|
| A second complete language catalog | Translation quality, terminology ownership, and completeness review would dominate the infrastructure milestone. | Add in v1.x after the English catalog and fallback behavior pass coverage tests. |
| Translation of Paper/plugin/RCON output | Server text is open-ended, plugin-specific, and valuable as exact diagnostic evidence. Translation also breaks copy/paste matching against logs and documentation. | Keep permanently outside client localization; plugins may provide their own localized output upstream. |
| Browser-language auto-selection | The committed first-visit rule is deterministic English, and implicit selection makes support screenshots and reproduction less predictable. | Consider only after product policy explicitly changes. |
| Runtime-downloaded catalogs | Remote catalogs introduce availability, caching, version skew, and content-integrity concerns. | Consider when catalog releases need an independent deployment lifecycle. |
| Translation management service | A service adds credentials, synchronization, and release-process dependencies before a translation team exists. | Consider after multiple maintained locales and named localization owners exist. |
| Runtime machine translation | Administrative controls require stable terminology and exact intent; generated wording can misrepresent destructive actions. | Keep outside the admin plane. |
| Global DOM text replacement | Text matching is fragile, loses context, misses attributes and dynamic nodes, and can alter raw server output. | Use explicit keys and rendering functions throughout. |
| Independent manual maintenance of two catalogs | Parallel copies create silent key and wording drift between 1.8 and 1.12. | Use one canonical content source or an enforced copy/parity workflow. |
| Full ICU message framework | Current v1 scope has one complete locale and zero-dependency constraints. A small catalog, interpolation helper, and native `Intl` APIs cover the committed behavior. | Reassess when plural categories or grammatical selection exceed the local helper's clarity. |
| RTL layout certification | RTL requires layout, icon direction, focus order, and mixed-content testing beyond catalog plumbing. | Schedule with the first committed RTL locale. |
| Broad modal interaction redesign | Focus trapping, animation, component architecture, and visual redesign form a separate accessibility/UI project. | Preserve existing behavior in v1 while localizing names and messages; plan wider remediation independently. |
| Localization of command tokens and config enums | Translated protocol values can produce rejected commands or unintended settings. | Keep stable values internal and translate display labels only. |

## Behavioral Expectations by Surface

### Static HTML

- English appears in source markup for all initial headings, labels, controls, helper text, placeholders, and empty states.
- Each translatable node or attribute has a stable catalog key. Keys describe meaning, such as `players.actions.kick`, instead of embedding current wording.
- Structural markup remains stable during locale changes so focus, expanded sections, and entered values survive.

### Dynamic JavaScript

- Every client-authored string generated in `admin.js` resolves through the active locale.
- Code passes semantic data into translations: `{player}`, `{count}`, `{seconds}`, `{mode}`, and `{error}`. Display strings never become command tokens.
- Historical console entries retain the text captured when they were written. New client-authored entries use the current locale. Raw server entries remain verbatim throughout. This keeps an operational log temporally stable.
- Locale-sensitive numeric and date formatting uses native `Intl` APIs with the active locale where the UI presents human-formatted values. Server timestamps and protocol values remain intact when fidelity matters.

### Dialogs, Toasts, and Errors

- Modal content is translated as a complete interaction, including title, body, labels, placeholders, validation, cancel, and confirmation text.
- Destructive confirmation wording names the action and target explicitly in the locale catalog.
- Toasts localize severity and client context while embedding raw server details unchanged.
- Missing translations never erase action labels or accessible names.

### Document and Accessibility Metadata

- `<html lang>` tracks the active locale so browsers and assistive technologies apply the correct pronunciation and language processing.
- `document.title` and the HTML `<title>` represent the localized admin page identity.
- `aria-label`, accessible dialog names, form labels, button titles, and iframe titles receive the same coverage as visible text.
- Dynamic success and failure notifications use status-message semantics appropriate to their urgency.

### Locale Selection and Persistence

- The header contains a native locale selector populated from the bundled locale registry.
- English (`en`) is the sole v1 entry and the first-visit default. The visible control establishes a stable future location for additional complete catalogs.
- A valid stored locale loads on subsequent visits. Unknown locale codes, stale values, and storage access failures resolve to English.
- Locale changes apply immediately and persist after successful selection.
- Catalogs use stable locale identifiers and human-readable self-names, enabling future entries without changing selector logic.

### Fallback Contract

Use this deterministic resolution order for every key:

1. Active locale value.
2. English value.
3. Visible diagnostic representation of the key.

English completeness is therefore a release invariant. A future partial locale can be used safely during development while production selection remains limited to complete catalogs.

### Mirrored-Version Parity

- `web-1.8` and `web-1.12` ship identical locale identifiers, key sets, fallback behavior, selector behavior, metadata behavior, and raw-output boundaries.
- Shared behavior changes land in both trees in the same change set.
- Release verification compares the mirrored admin assets and reports exact drift. Existing byte identity provides a strong baseline.
- Game-version-specific wording may use explicit keyed variants only when a real product difference appears. The current milestone has no known wording divergence.

## Feature Dependencies

```text
English catalog + stable keys
├── deterministic fallback
├── static HTML binding
├── dynamic JavaScript messages
├── dialog/toast coverage
├── metadata and ARIA coverage
└── future locale catalogs

Locale registry
├── header selector
├── localStorage validation
└── <html lang> / Intl locale selection

Semantic state separated from display labels
├── live switching without workflow loss
├── safe command generation
└── re-rendered dynamic controls

String-source classification
├── localized client framing
└── verbatim Paper/plugin/RCON output

Canonical mirrored assets or parity check
└── equivalent web-1.8 and web-1.12 releases
```

The English catalog and string-source classification are the two foundational dependencies. Locale selection can ship only after fallback and valid-code handling exist. A second locale should wait until the complete surface inventory and mirrored parity checks are reliable.

## MVP Definition

### Launch With — v1.0

1. A complete English catalog and English source-markup baseline.
2. A small zero-dependency locale registry, key lookup, named interpolation, and deterministic English fallback.
3. A header native selector with English as the only bundled complete locale.
4. `localStorage` persistence with validation and safe English recovery.
5. Immediate, state-preserving locale application.
6. Coverage for all static HTML and dynamic JavaScript UI text.
7. Coverage for dialog, toast, validation, loading, empty, success, and failure text.
8. Localized `<html lang>`, document title, placeholders, element titles, iframe title, labels, and ARIA names.
9. Native locale-aware number/date formatting where the UI owns formatting.
10. A documented and enforced boundary that preserves raw Paper/plugin/RCON output and command semantics.
11. Equivalent assets and catalog keys in `web-1.8` and `web-1.12`, backed by a repeatable parity check.
12. Manual acceptance checks across authentication, player, world, TPS, config, modal, toast, command, status, and error flows in both versions.

### Add After Validation — v1.x

- The first additional complete locale, with a named translation owner and terminology review.
- Pseudo-locale or automated text-expansion testing to expose clipping and concatenation issues.
- Automated missing-key and unused-key reporting if catalog growth makes manual review costly.
- Locale-aware plural categories beyond the small v1 needs, driven by the first added language.

### Future Consideration — v2+

- RTL layout support and certification.
- Independent catalog delivery or translation-management integration.
- Rich grammatical selection backed by a proven multi-language requirement.
- Per-user server-side locale preferences when browser-local persistence becomes insufficient for shared workstations.

## MVP Acceptance Boundary

The milestone is complete when an operator can load either admin version, see English immediately, select and persist a valid locale, encounter English fallback for every missing lookup, and complete all existing workflows with translated client UI and untouched server-originated content. Adding another human-language catalog is explicitly deferred. Translating server, plugin, and RCON payloads remains outside the product boundary.

The following failures block release:

- Any blank, undefined, raw key, or stale-language label on an operational control under normal English use.
- Any command or configuration payload derived from translated display text.
- Any translated or rewritten Paper/plugin/RCON payload.
- Any untranslated client-authored modal, toast, title, placeholder, or accessibility name.
- Any locale switch that clears auth, input, selection, or current server state.
- Any key-set or behavior drift between `web-1.8` and `web-1.12`.

## Prioritization

| Priority | Features | Rationale |
|---|---|---|
| P0 | English completeness, fallback, raw-output boundary, stable command semantics, mirrored parity | These protect operability and diagnostic fidelity. |
| P0 | Static/dynamic/dialog/toast/metadata/ARIA coverage | Partial coverage makes the feature unpredictable and inaccessible. |
| P1 | Selector, persistence, live state-preserving application | These establish the operator-facing locale behavior and future catalog path. |
| P1 | Native number/date formatting and visible missing-key diagnostics | These improve consistency and make defects easier to catch. |
| P2 | Pseudo-localization and automated catalog hygiene | These become more valuable as additional locales arrive. |
| Deferred | Additional locales, RTL, remote catalogs, translation platform, ICU-scale grammar | These require product demand, language ownership, or broader infrastructure. |

## Testing Implications

The existing project relies mainly on manual verification, so v1 should define a compact matrix and automate the high-value invariants:

- Static check: English catalog has all referenced keys; both version trees have the same key set and equivalent admin assets.
- Startup check: fresh storage, valid `en`, unknown locale, malformed value, and blocked storage all produce usable English.
- Surface check: static labels, dynamic status, dialogs, toasts, validation, document title, `lang`, placeholders, `title`, and ARIA names update together.
- State check: locale application preserves token/session state, entered text, selected entities, expanded panels, and fetched status.
- Fidelity check: representative RCON success, Paper error, plugin output, player names, MOTD, seed, and command strings remain byte-for-byte unchanged inside localized wrappers.
- Parity check: repeat the same workflows on ports/assets for both `web-1.8` and `web-1.12`.

## Sources

### Repository evidence

- `.planning/PROJECT.md` — milestone constraints and product scope.
- `.planning/codebase/ARCHITECTURE.md` — admin-plane architecture and server-output flow.
- `.planning/codebase/STRUCTURE.md` — mirrored web trees and file responsibilities.
- `.planning/codebase/CONVENTIONS.md` — native HTML/JavaScript/CSS conventions and mirrored-file expectations.
- `.planning/codebase/TESTING.md` — current verification practices and risk areas.
- `web-1.8/admin.html`, `web-1.12/admin.html` — static, metadata, form, modal, iframe, and accessibility text surfaces.
- `web-1.8/admin.js`, `web-1.12/admin.js` — dynamic messages, dialogs, toasts, status rendering, commands, and raw API/RCON responses.

### Official and primary references

- [W3C WCAG 2.2: Understanding Language of Page](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html) — supports keeping the page language programmatically identifiable through `lang`.
- [W3C WCAG 2.2: Understanding Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) — supports programmatic announcement of dynamic success and error status without forced focus changes.
- [WAI-ARIA Authoring Practices: Modal Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) — supports accessible names and descriptions for modal interactions.
- [W3C WAI Forms Tutorial: Labels](https://www.w3.org/WAI/tutorials/forms/labels/) — supports explicit and meaningful labels for form controls.
- [MDN: `Window.localStorage`](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) — documents origin-scoped persistence and storage access exceptions, supporting validation and failure recovery.
- [MDN: HTML `lang` global attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/lang) — documents language metadata behavior.
- [MDN: `Intl.NumberFormat`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat) — documents native locale-sensitive number formatting.
- [WHATWG HTML: The `title` element](https://html.spec.whatwg.org/multipage/semantics.html#the-title-element) — defines the document title as navigation and identification metadata.

## Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| Current surface and mirrored-file facts | HIGH | Direct inspection and byte comparison of required repository files. |
| Accessibility and browser API expectations | HIGH | W3C, WAI-ARIA, WHATWG, and MDN primary documentation. |
| MVP technical fit | HIGH | Matches the repository's native, dependency-free architecture and milestone constraints. |
| Operator preference ordering | MEDIUM | Inferred from operational admin workflows and diagnostic needs; no project-specific interviews or telemetry were available. |
| Future-locale requirements | LOW | Language choice, translation ownership, RTL demand, and grammatical complexity remain undecided. |
