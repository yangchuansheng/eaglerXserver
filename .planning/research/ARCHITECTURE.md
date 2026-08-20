# Architecture Research

**Domain:** Internationalization for the dependency-free EaglercraftX admin plane
**Researched:** 2026-08-20
**Confidence:** HIGH for codebase integration; HIGH for browser-platform recommendations backed by standards

## Standard Architecture

### System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│ admin.html: English-first document shell                            │
│ data-i18n bindings · language selector · semantic HTML/ARIA         │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ load before admin.js
┌───────────────────────────────▼──────────────────────────────────────┐
│ admin-i18n.js: one global AdminI18n boundary                        │
│ locale registry · English catalog · fallback · interpolation        │
│ localStorage · DOM attribute application · Intl formatting          │
└──────────────────┬────────────────────────────┬──────────────────────┘
                   │ t(key, params)             │ locale-change event
┌──────────────────▼────────────────────────────▼──────────────────────┐
│ admin.js: feature controllers and renderers                         │
│ auth/status · dialogs · world/seed/structures · players/TPS/config │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ fetch / management commands
┌───────────────────────────────▼──────────────────────────────────────┐
│ Existing admin API and RCON bridge                                  │
│ Structured UI state is localized; Paper/plugin/RCON payloads stay  │
│ opaque and are rendered verbatim                                    │
└──────────────────────────────────────────────────────────────────────┘

             same source payload copied and parity-checked
       web-1.8/admin*  ◄──────────────────────►  web-1.12/admin*
```

The recommended design adds one small presentation service and leaves the current API, command construction, authentication, polling, and backend boundaries intact. `admin-i18n.js` should be an IIFE that exposes `window.AdminI18n`, matching the current global-function and inline-handler architecture. Native ES modules or a bundler would add deployment and ordering changes without improving this milestone.

### Current Rendering and Message Paths

| Surface | Current path | i18n integration point |
|---------|--------------|------------------------|
| Initial document | `web-*/admin.html:2-241` owns title, headings, buttons, notes, placeholders, dialog shells, and accessibility labels | Keep complete English source text in HTML; attach `data-i18n`, `data-i18n-placeholder`, `data-i18n-title`, and `data-i18n-aria-label` keys |
| Console messages | `log()` in `admin.js:35-48` adds a localized timestamp and text node | Keep `log(text, class)` as the raw sink; add `logKey(key, params, class)` or translate at managed call sites |
| Toasts | `toast()` in `admin.js:50-56` writes a single text node | Keep the sink text-only; pass translated UI messages and raw backend errors according to message ownership |
| Connection/hero state | `setStatus()` and `startHeroPulse()` in `admin.js:58-94` generate multiple related strings | Pass semantic state plus parameters into one renderer, then derive status, signal, note, and pulse strings from keys |
| Bootstrap/authentication | `init()` and auth helpers in `admin.js:168-325` mix fetch state with user-facing Chinese messages | Initialize locale before `init()`; replace managed strings with keys while preserving auth control flow |
| World and Seed Map | `admin.js:327-595` renders hints, link states, clipboard outcomes, and world values | Translate labels and state sentences; keep seed, URLs, coordinates, dimensions, and server values raw |
| Structure search | `admin.js:712-879` builds source labels, empty states, summaries, and result cards | Translate structure type labels and UI grammar; keep returned names/coordinates and command previews raw where sourced externally |
| Generic action dialog | `admin.js:1051-1285` creates fields and renders title, description, labels, hints, preview labels, and buttons | Change config schema to semantic keys (`titleKey`, `descriptionKey`, `confirmKey`, `labelKey`, `hintKey`, `placeholderKey`) and translate during every render |
| Command-specific dialogs | `admin.js:1287-1754` supplies many literal labels, validation errors, and confirmations | Migrate configurations in groups after the generic renderer accepts keys |
| RCON command boundary | `send()` in `admin.js:1757-1788` sends commands and writes `d.response` to `log()` | Preserve command text and `d.response` verbatim; localize only client-owned wrappers such as network-failure context |
| Polling/renderers | `admin.js:1809-1980` renders players, TPS, world data, and Seed data | Render from `ONLINE_PLAYERS`, `WORLD_INFO_CACHE`, `WORLD_SEED`, `SERVER_INFO`, and latest responses through keyed templates |
| Notifications/config/restart | `admin.js:1982-2203` combines API messages, fallback messages, and local state | Assign ownership explicitly: client fallback text uses catalog keys; server-provided `error`/`message` fields stay raw |
| Locale-sensitive formatting | `formatNumber()` near `admin.js:510` fixes `zh-CN`; `log()` uses browser-default `toLocaleTimeString()` | Route number and time formatting through `AdminI18n` with the active locale |

### Component Responsibilities

| Component | Responsibility | Recommended implementation |
|-----------|----------------|----------------------------|
| English catalog | Canonical key set and complete fallback text | Flat object in `admin-i18n.js`, grouped by key prefixes such as `header.*`, `auth.*`, `dialog.*`, `world.*`, `players.*` |
| Locale registry | Lists selectable locales and their display names/catalogs | Ordered array or object containing only complete `en` for v1.0; selector options derive from it |
| Translation runtime | Locale resolution, English fallback, interpolation, formatting, and change notification | Frozen `window.AdminI18n` API with private state inside an IIFE |
| Static DOM binder | Applies translations to text and translatable attributes | `apply(root)` scans the four `data-i18n*` attributes; use `textContent` and `setAttribute` |
| Language selector | Lets the user choose and persist a locale | Header `<select id="locale-select">`; options generated from the registry; value stored under `eaglerx_admin_locale` |
| Shared UI sinks | Console, toast, status, modal, and action-dialog output | Keep low-level sinks string-based and translate at the semantic boundary |
| Feature renderers | Rebuild localized dynamic DOM from cached state | Small `render*()` functions for auth status, world, Seed, structures, players, TPS, and active dialogs |
| Raw-output boundary | Protects Paper/plugin/RCON output, player names, commands, and backend payload text | Direct `textContent` assignment with no catalog lookup or interpolation pass |
| Mirror guard | Keeps the 1.8 and 1.12 web trees byte-identical | Regression test comparing `admin.html`, `admin.css`, `admin.js`, and `admin-i18n.js` |

## Recommended Project Structure

```text
web-1.8/
├── admin.html          # English source shell, i18n attributes, selector, script order
├── admin.css           # Selector styling and responsive header fit
├── admin-i18n.js       # Catalog, registry, fallback, persistence, DOM binding
└── admin.js            # Existing behavior with keyed managed UI messages
web-1.12/
├── admin.html          # Exact copy of web-1.8/admin.html
├── admin.css           # Exact copy of web-1.8/admin.css
├── admin-i18n.js       # Exact copy of web-1.8/admin-i18n.js
└── admin.js            # Exact copy of web-1.8/admin.js
tests/
└── test_regressions.py # Mirror, catalog, binding, and hard-coded-text guards
```

### Structure Rationale

- **One `admin-i18n.js` per served web root:** the runtime selector makes only the selected `web-*` directory available through the `web/` symlink. A physical copy ensures each version is independently deployable through the existing static server.
- **Catalog and runtime in one file for v1.0:** English is the sole complete locale, so a directory of one-file-per-locale adds script-order and parity surface. The registry keeps a clean later split point once a second complete locale arrives.
- **English remains in `admin.html`:** users and assistive technology receive a coherent page before JavaScript runs, and runtime failure leaves a usable English admin shell.
- **Tests stay in the existing Python suite:** the repository already uses `unittest`; file parity and static key coverage require no JavaScript test dependency.
- **Backend files remain unchanged:** locale is browser presentation state and carries no API or RCON semantics.

### Expected Modified Files

| File | Change |
|------|--------|
| `web-1.8/admin-i18n.js` | New runtime and English catalog |
| `web-1.8/admin.html` | English source copy, bindings, selector, and `admin-i18n.js` before `admin.js` |
| `web-1.8/admin.js` | Keyed managed strings, locale-aware formatters, re-render hooks, raw-output boundary |
| `web-1.8/admin.css` | Compact header selector styling at desktop, 820px, and 520px layouts |
| `web-1.12/admin-i18n.js` | Exact mirror |
| `web-1.12/admin.html` | Exact mirror |
| `web-1.12/admin.js` | Exact mirror |
| `web-1.12/admin.css` | Exact mirror |
| `tests/test_regressions.py` | Static contract and mirror verification |

## Architectural Patterns

### Pattern 1: English-First Catalog with Deterministic Fallback

**What:** Every managed string has a stable semantic key. Lookup checks the active catalog, then the English catalog, then returns a visible diagnostic token such as `[missing:key]`. Locale selection accepts registry entries only.

**When to use:** Static content, client-generated status, validation, dialogs, notifications, title, placeholders, button labels, and accessibility text.

**Trade-offs:** A flat catalog is easy to audit and diff. It places naming discipline on contributors and grows into a large object over time. Splitting locale files becomes useful after multiple complete catalogs exist.

**Example:**

```javascript
var catalogs = {
  en: {
    'status.connected': 'Connected',
    'players.online': '{count} players online'
  }
};

function t(key, params) {
  var catalog = catalogs[currentLocale] || catalogs.en;
  var template = catalog[key] || catalogs.en[key] || '[missing:' + key + ']';
  return interpolate(template, params || {});
}
```

Interpolation should replace named `{token}` placeholders with string values. Values enter text nodes through `textContent`; templates should never become HTML.

### Pattern 2: Declarative Static Bindings

**What:** HTML declares the translation key beside the English fallback text. The runtime applies bindings after load and after each locale change.

**When to use:** Stable DOM nodes already present in `admin.html`.

**Trade-offs:** Reviewers can see both the English page and key mapping in one file. Repeated scans are inexpensive at this page size. Dynamic fragments still need renderer-level translation.

**Example:**

```html
<html lang="en">
<title data-i18n="page.title">EaglercraftX Server Admin</title>
<button data-i18n="common.save" data-i18n-aria-label="config.saveAria">Save</button>
<input data-i18n-placeholder="console.commandPlaceholder">
```

`apply(root)` should support text, `placeholder`, `title`, and `aria-label` explicitly. A generic translated-attribute mechanism would widen the security and audit surface.

### Pattern 3: Translate at Semantic Render Boundaries

**What:** State-oriented functions receive semantic values and call `t()` while rendering. Shared components receive keys and parameters, especially the generic action dialog.

**When to use:** Status displays, action-dialog schemas, empty states, player/TPS/world views, and repeated notifications.

**Trade-offs:** Locale changes can re-render current state consistently. The migration touches many literal call sites, so it should proceed by renderer family with a hard-coded-string scan after each phase.

**Example:**

```javascript
showActionDialog({
  titleKey: 'dialog.teleport.title',
  descriptionKey: 'dialog.teleport.description',
  confirmKey: 'dialog.teleport.confirm',
  fields: [{
    name: 'player',
    labelKey: 'field.player.label',
    placeholderKey: 'field.player.placeholder'
  }]
});
```

Store keys in `ACTION_DIALOG.config`. This lets an open dialog redraw labels immediately when the locale changes.

### Pattern 4: Explicit Raw-Data Boundary

**What:** UI-owned prose uses catalog keys. Server-owned values flow directly to text nodes. Raw values include `d.response`, API `error`/`message` text, player names, plugin names, version text, entered commands, command previews, seeds, coordinates, and URLs.

**When to use:** Every API response and RCON rendering path.

**Trade-offs:** Operators retain exact diagnostic output and searchable command responses. Mixed messages need separate DOM spans or a localized prefix concatenated with the untouched raw value.

**Example:**

```javascript
logKey('console.commandSent', { command: cmd }, 'cmd');
log(d.response || AdminI18n.t('console.emptyOutput'), 'out');

var prefix = document.createElement('span');
prefix.textContent = AdminI18n.t('error.requestFailed') + ': ';
var detail = document.createElement('span');
detail.textContent = String(d.error || 'unknown');
```

`console.emptyOutput` is client-owned fallback text. A present `d.response` remains byte-for-byte equivalent at the string level.

### Pattern 5: Re-render from Existing Caches on Locale Change

**What:** A locale-change callback reapplies static bindings and re-runs renderers using existing state. It performs no fetch and sends no command.

**When to use:** Header/status, hero pulse, current dialog, world card, Seed panel, last structure result, player list, TPS, and configuration labels.

**Trade-offs:** Reusing the current caches keeps switching immediate and side-effect free. A few current functions combine fetching and rendering, so thin pure render helpers should be extracted only where locale switching requires them.

Recommended callback order:

1. Update `document.documentElement.lang`, title, selector, and static `data-i18n*` bindings.
2. Re-render connection/auth and hero state from `TOKEN` and `SERVER_INFO`.
3. Re-render world, Seed, structures, players, TPS, and config from existing caches.
4. Re-render `ACTION_DIALOG` when open while preserving current field values and focus.
5. Restart or immediately refresh the hero pulse text so its next frame uses the active locale.

## Data Flow

### Startup Flow

```text
Browser parses complete English admin.html
    ↓
admin-i18n.js reads eaglerx_admin_locale from localStorage
    ↓ validate against registry; fallback to en
AdminI18n initializes <html lang>, title, selector, and static bindings
    ↓
admin.js loads and init() performs the existing status/auth flow
    ↓
Feature renderers call AdminI18n.t() for client-owned prose
    ↓
API/RCON values are inserted as raw text
```

### Locale Change Flow

```text
User selects locale in header
    ↓
AdminI18n.setLocale(locale)
    ├── validate registry key
    ├── persist localStorage
    ├── update document language/title/static bindings
    └── notify admin.js subscribers
             ↓
       re-render cached UI state and active dialog
             ↓
       network state, timers, token, field values, and raw console history remain intact
```

Existing console history should remain as originally emitted. Rewriting past raw output risks altering diagnostics, and rewriting past client messages adds complexity with little operator value. New entries use the current locale.

### Command and Response Flow

```text
Localized button/dialog label
    ↓ user action
Existing command builder creates raw Minecraft command
    ↓
send(cmd) → /api/rcon → Paper/plugin
    ↓
d.response / d.error
    ↓
Raw text node in console/toast, with optional localized client-owned prefix
```

### State Management

```text
AdminI18n private state                 Existing admin.js state
├── currentLocale                      ├── TOKEN / SERVER_INFO
├── locale registry                    ├── WORLD_INFO_CACHE / WORLD_SEED
└── catalogs                           ├── LAST_STRUCTURE_RESULT
        │ locale-change callback       ├── ONLINE_PLAYERS / CONFIG_CACHE
        └─────────────────────────────►└── ACTION_DIALOG
                                              │
                                              ▼
                                      focused render functions
```

Locale state belongs in `admin-i18n.js`; operational state stays in `admin.js`. Auth tokens continue using `sessionStorage`, while the locale uses `localStorage` because preference persistence should span browser sessions. Storage access should remain inside `try/catch`, following the current defensive storage style.

### Runtime API Contract

Keep the public surface small:

```javascript
window.AdminI18n = {
  t: t,
  getLocale: getLocale,
  setLocale: setLocale,
  getLocales: getLocales,
  apply: apply,
  onChange: onChange,
  formatNumber: formatNumber,
  formatTime: formatTime
};
```

`getLocales()` should return selector metadata rather than mutable catalog objects. The English catalog remains the canonical test oracle.

## Scaling Considerations

For this feature, catalog size and contributor count matter more than runtime user count. All translation work runs in the browser and the page has a small fixed DOM.

| Scale | Architecture adjustment |
|-------|-------------------------|
| 1 complete locale | Keep registry, English catalog, and runtime in `admin-i18n.js` |
| 2-5 complete locales | Consider one script per catalog loaded before the runtime, while preserving the same registry API and English fallback |
| 5+ locales or frequent translators | Add a repository generation/validation script that emits mirrored browser catalogs from one canonical source; keep generated files dependency-free at runtime |

### Scaling Priorities

1. **First pressure point — key drift:** HTML/JavaScript references can outpace catalog updates. Add static key coverage and English completeness tests before adding a second locale.
2. **Second pressure point — mirror drift:** duplicated web trees can diverge during routine edits. Make parity a required regression test for all four admin assets.
3. **Third pressure point — catalog review size:** split locale data only when multiple real catalogs make the single file difficult to review.

## Anti-Patterns

### Anti-Pattern 1: Inferring Keys from Display Text

**What people do:** Use English sentences as catalog keys or reverse-map current DOM text.

**Why it fails here:** Copy edits become breaking identifier changes, repeated phrases lose context, and active-dialog rerendering becomes ambiguous.

**Recommended approach:** Stable semantic keys with English values in the canonical catalog.

### Anti-Pattern 2: Translating API and RCON Payloads

**What people do:** Pass every string through `t()` or search-and-replace known Paper messages.

**Why it fails here:** Plugin output is open-ended, operational diagnostics lose fidelity, player-provided text can collide with keys, and command results become harder to search.

**Recommended approach:** Translate browser-owned framing and render server-owned values verbatim.

### Anti-Pattern 3: Locale Checks Spread Across Features

**What people do:** Add `if (locale === ...)` branches throughout `admin.js`.

**Why it fails here:** The current file already has many dynamic-message paths, so branching multiplies test combinations and makes fallback inconsistent.

**Recommended approach:** One lookup service and data-driven templates.

### Anti-Pattern 4: Fetching Again on Language Change

**What people do:** Re-run initialization and polling functions to obtain data for translated views.

**Why it fails here:** Switching language can duplicate timers, open auth flows, send management requests, and disturb current dialog input.

**Recommended approach:** Pure rerenders from existing caches and preserved form values.

### Anti-Pattern 5: Independent Manual Edits in Both Web Trees

**What people do:** Apply the same conceptual edit separately to `web-1.8` and `web-1.12`.

**Why it fails here:** The current files are byte-identical and runtime version selection expects equivalent admin behavior. Separate edits create silent copy drift.

**Recommended approach:** Edit one canonical tree during each change, copy the four admin assets once, then run byte-parity tests.

### Anti-Pattern 6: Rendering Catalog Values as HTML

**What people do:** Insert translated strings with `innerHTML` to support formatting.

**Why it fails here:** Catalog content gains markup privileges and interpolated values can cross an unsafe boundary.

**Recommended approach:** Use `textContent`, explicit DOM elements, and attribute-specific setters.

## Integration Points

### Browser Platform Services

| Service | Integration pattern | Notes |
|---------|---------------------|-------|
| HTML `lang` | Set `<html lang="en">` in source and update it when locale changes | Supports assistive technology and language-aware browser behavior |
| Web Storage | Persist `eaglerx_admin_locale` with `localStorage` | Preference is origin-scoped and survives browser sessions; storage exceptions need a safe English fallback |
| ECMA-402 `Intl` | Construct `Intl.NumberFormat(activeLocale)` and `Intl.DateTimeFormat(activeLocale)` | Replaces the fixed `zh-CN` number formatter and aligns new console timestamps with selected locale |
| Accessible names | Translate `aria-label`, visible labels, placeholders, and `title` through explicit bindings | Visible instructions and programmatic labels should change together |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `admin.html` → `admin-i18n.js` | `data-i18n*` attributes and selector element | HTML carries English fallback content |
| `admin-i18n.js` → `admin.js` | `window.AdminI18n` API and locale-change callback | Load i18n script before `admin.js` |
| `admin.js` → shared UI sinks | Translated strings or keys at semantic boundaries | Keep `log()` and `toast()` capable of raw text |
| Action configs → dialog renderer | Key fields plus interpolation parameters | Active config retains keys for rerender |
| Cached state → feature renderers | Direct function calls | Locale changes perform local rendering only |
| `send()`/API helpers → DOM | Raw response fields | Preserve exact Paper/plugin/RCON output |
| `web-1.8` ↔ `web-1.12` | Physical file copy plus test-enforced equality | Both runtime versions ship identical admin behavior |

## Low-Risk Build Order

### 1. Establish the Runtime Contract

Create `web-1.8/admin-i18n.js` with the English catalog, locale registry, deterministic fallback, named interpolation, safe storage access, explicit DOM bindings, and locale-aware number/time formatters. Add the selector shell and load this script before `admin.js`.

**Verification:** syntax-check the new file; confirm empty, valid, and invalid stored locale values all resolve to `en`; confirm missing active-locale keys resolve through English.

### 2. Convert the Static English Shell

Replace the Chinese source copy in `admin.html` with complete English and add explicit translation attributes for text, title, placeholder, and ARIA surfaces. Style the header selector at existing desktop, 820px, and 520px breakpoints.

**Verification:** load the page with JavaScript disabled or with `admin-i18n.js` intentionally blocked and inspect a complete English shell; scan every static translatable attribute; check keyboard label association and responsive header fit.

### 3. Migrate Shared Message Sinks and State Renderers

Integrate auth bootstrap, `setStatus()`, hero pulse, `toast()` call sites, managed console messages, and locale-aware formatting. Introduce semantic state rendering where one state currently produces several strings.

**Verification:** exercise RCON disabled, awaiting authentication, authentication success, authentication failure, and expired-token paths; switch locale state during each path and observe consistent title/status/ARIA output.

### 4. Migrate the Generic Dialog System

Teach `renderActionFields()` and `showActionDialog()` to consume key-based configuration, then migrate command-specific dialog definitions in related groups. Preserve input values, command previews, and focus during an active locale rerender.

**Verification:** cover text, number, select, checkbox, confirmation, validation, cancel, and submit variants; assert generated Minecraft commands remain identical before and after localization.

### 5. Migrate Feature Renderers

Move world, Seed Map, structures, players, TPS, whitelist, configuration, notification, and restart prose to keys. Extract focused render helpers only where existing fetch/render coupling blocks a cache-only locale refresh.

**Verification:** populate each cache, change locale without network activity, and confirm visible state redraws while seeds, coordinates, names, versions, URLs, commands, and backend messages retain their source values.

### 6. Mirror Once and Add Regression Guards

Copy the four completed `admin*` assets from `web-1.8` to `web-1.12`. Extend `tests/test_regressions.py` with parity, referenced-key coverage, English catalog completeness, duplicate-key detection, and a targeted managed-Chinese-literal scan. Keep the scan allowlist explicit for comments, raw protocol fixtures, or future catalog values.

**Verification:** byte-compare all four pairs and run the full Python test suite.

### 7. Browser Acceptance Matrix

Run the admin page against both `MINECRAFT_VERSION=1.8` and `MINECRAFT_VERSION=1.12`. Check fresh storage, persisted storage, invalid storage, a temporary incomplete test catalog, active dialogs, keyboard use, responsive widths, and representative successful and failed RCON actions.

**Verification:** record the matrix below as release evidence.

## Concrete Verification Approach

### Automated Checks

1. `node --check web-1.8/admin-i18n.js` and `node --check web-1.8/admin.js`.
2. The same syntax checks for `web-1.12`.
3. `python3 -m unittest discover` for existing and new regression coverage.
4. Byte equality for `admin.html`, `admin.css`, `admin.js`, and `admin-i18n.js` across both web trees.
5. Parse all `data-i18n*` values and explicit `t()`/key-config references, then require every key in the English catalog.
6. Require unique catalog keys and valid `{placeholder}` agreement between English fallback and test catalogs.
7. Scan managed HTML/JavaScript surfaces for remaining Chinese literals, with a narrow reviewed allowlist.

### Browser Matrix

| Scenario | Expected result |
|----------|-----------------|
| Fresh profile | English selected; complete English UI; `<html lang="en">`; English title |
| Stored `en` | English restored before operational rendering |
| Stored unknown locale | English fallback; selector synchronized to `en` |
| Temporary catalog missing keys | Present translations render; missing entries use English |
| Locale switch with open action dialog | Labels and accessibility text redraw; typed values, focus, and preview remain |
| Locale switch after polling | World, Seed, structure, player, TPS, and config views redraw from cache; fetch count stays unchanged |
| RCON command response | Paper/plugin response text matches the API payload |
| Error response | Backend detail remains raw; browser-owned framing follows active locale |
| Console history | Existing entries remain unchanged; new managed entries use current locale |
| Widths 520px, 820px, desktop | Header selector remains visible, usable, and aligned with current navigation |
| Both server versions | Identical admin presentation and behavior on 1.8 and 1.12 runtime selections |

### Release Gate

The milestone is ready when all catalog references resolve, both asset trees are byte-identical, the automated suite passes, the browser matrix passes on both server versions, and sampled raw RCON/Paper/plugin output remains unchanged.

## Sources

- WHATWG HTML Living Standard, language attributes: https://html.spec.whatwg.org/multipage/dom.html#the-lang-and-xml:lang-attributes
- WHATWG HTML Living Standard, Web Storage and `localStorage`: https://html.spec.whatwg.org/multipage/webstorage.html#the-localstorage-attribute
- W3C WCAG 2.2, Understanding SC 3.1.1 Language of Page: https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html
- W3C WCAG 2.2, Understanding SC 3.3.2 Labels or Instructions: https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html
- W3C WAI-ARIA 1.2, `aria-label`: https://www.w3.org/TR/wai-aria-1.2/#aria-label
- ECMA-402, ECMAScript Internationalization API Specification: https://tc39.es/ecma402/
- Repository source: `web-1.8/admin.html`, `web-1.8/admin.js`, mirrored `web-1.12` files, and `tests/test_regressions.py` as inspected on 2026-08-20

---
*Architecture research for: v1.0 Admin i18n*
*Researched: 2026-08-20*
