# Stack Research

**Domain:** Dependency-free browser administration UI internationalization
**Researched:** 2026-08-20
**Confidence:** HIGH

## Recommended Stack

Use the existing browser stack plus one project-owned locale catalog in `admin.js`. This keeps the milestone inside the current classic-script deployment model, preserves the self-contained Docker image, and gives the roadmap a direct path to English fallback, persisted selection, dynamic text, and accessibility coverage.

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| HTML `lang` and `data-*` attributes | HTML Living Standard | Declare document language and bind static elements to translation keys | They fit the current static `admin.html` files and keep translation intent visible beside each element. |
| Native `<select>` | HTML Living Standard | Header locale picker | It supplies keyboard interaction, focus behavior, form semantics, and broad browser compatibility with minimal code. |
| Web Storage `localStorage` | Living Standard | Persist the selected locale across browser sessions | The requirement calls for durable client-side preference storage; one namespaced string is the complete storage need. |
| Project-owned flat message catalog | Internal v1 | Message lookup, English fallback, locale metadata, and simple interpolation | The current UI has one complete locale, one page, one script, and no package pipeline. A small helper covers the exact requirement. |
| ECMA-402 `Intl.NumberFormat` and locale-aware time formatting | Current browser implementation | Format admin-authored numbers and timestamps using the active locale | The existing code already formats numbers and time in the browser; routing these calls through the selected locale removes the current `zh-CN` hard-code. |
| CSS in `admin.css` | Existing project baseline | Style the header selector | The selector belongs in the current mirrored stylesheet and requires only component-level rules. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Browser built-ins | Target browser | DOM updates, storage, selection, and locale-aware formatting | Use throughout v1. |
| Runtime package additions | 0 | Preserve the current dependency boundary | Keep this count at zero for v1. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `node --check` | Parse both mirrored JavaScript assets | Run against `web-1.8/admin.js` and `web-1.12/admin.js`. It validates syntax without executing browser globals. |
| Python 3 `unittest` plus standard library | Add catalog and asset-integrity checks | Extend the existing test suite with key coverage, fallback metadata, duplicate-key, and mirror-parity assertions. |
| `cmp -s` | Enforce byte-identical mirrored admin assets | Check HTML and JavaScript on every i18n change; include CSS when selector styling changes. |
| `rg --pcre2` | Audit remaining authored CJK strings and direct user-facing literals | Maintain a narrow allowlist for protocol values, examples, and server-originated text boundaries. |
| Browser DevTools | Verify runtime switching, storage, accessibility attributes, and raw output behavior | Exercise the actual origin used in production because Web Storage is scoped by scheme, host, and port. |

## Recommended Catalog Shape

Keep the catalog in the existing classic `admin.js` file. A separate runtime file adds another mirrored asset and another load-order boundary while English is the sole complete locale.

```javascript
const DEFAULT_LOCALE = 'en';
const LOCALE_STORAGE_KEY = 'eagler.admin.locale.v1';

const LOCALES = {
  en: {
    label: 'English',
    dir: 'ltr',
    messages: {
      'meta.title': 'EaglercraftX Admin',
      'status.connected': 'Connected',
      'players.online': '{count} players online'
    }
  }
};
```

Use flat dot-delimited keys. Direct lookup keeps `t(key, params)` small, makes duplicate detection straightforward, and lets static checks compare all referenced keys with `LOCALES.en.messages`.

The lookup order should be:

1. Selected locale message.
2. English message.
3. Translation key as a visible diagnostic, accompanied by one console warning.

Interpolation should support named plain-text placeholders such as `{count}` through a small global regular expression. Catalog values remain plain text. `textContent` and `setAttribute` are the normal sinks; existing dynamic `innerHTML` paths must pass the completed translated string and every dynamic value through `escapeHtml()`.

## Integration Pattern for This Codebase

### Static DOM

Use explicit attributes with one purpose each:

- `data-i18n="nav.overview"` for text content.
- `data-i18n-placeholder="console.commandPlaceholder"` for inputs.
- `data-i18n-title="actions.fullscreen"` for title text.
- `data-i18n-aria-label="nav.admin"` for accessible names.

Keep readable English in the initial HTML. It gives the document a deterministic first paint and leaves usable copy when script initialization fails. Locale application then sets `document.documentElement.lang`, `document.documentElement.dir`, `document.title`, and all declared DOM translation targets.

### Dynamic UI

Store semantic state and translation keys separately from rendered text. Connection state, hero messages, empty states, TPS/player status, action-dialog configuration, toast messages, login flow, structure-search status, and notification text should call `t()` at render time. A locale switch should re-render current in-memory state without issuing new RCON or HTTP requests.

Inline handlers in `admin.html` currently carry authored Chinese success messages. Replace those message arguments with stable translation keys or derive the message key from the setting key. Commands, gamerule names, configuration keys, API paths, player names, coordinates, and mode values stay as protocol or data values.

The raw server boundary remains explicit: `d.response` and equivalent Paper/plugin/RCON payloads flow to the console unchanged. Local labels around those payloads use `t()`. Translation values never reinterpret command output.

### Locale Selection and Persistence

Populate the header selector from `LOCALES` so each added catalog automatically appears. Locale labels should use their own-language names. First visit resolves to `en`. Unsupported or malformed stored values resolve to `en`.

Wrap every `localStorage` read and write in `try/catch`. Browser privacy settings and origin policy can make storage access throw `SecurityError`; the active tab should continue with in-memory English in that case. The admin page can be served from ports 5200 and 5201, and storage treats those as separate origins, so verification should use the operator's production URL.

## Installation

Runtime and build installation remain unchanged. The implementation uses the assets and browser APIs already present in the repository.

```bash
node --check web-1.8/admin.js
node --check web-1.12/admin.js
python3 -m unittest discover -s tests -p 'test_*.py'
cmp -s web-1.8/admin.html web-1.12/admin.html
cmp -s web-1.8/admin.js web-1.12/admin.js
cmp -s web-1.8/admin.css web-1.12/admin.css
```

## Alternatives Considered

| Category | Recommended | Alternative | Adoption Point for Alternative |
|----------|-------------|-------------|--------------------------------|
| Message lookup | Flat project-owned catalog plus `t()` | Browser APIs alone | Browser APIs remain the persistence, metadata, control, and formatting layer; message lookup stays a project concern. |
| General i18n runtime | Minimal in-house helper | i18next | Adopt i18next when the product has several maintained locales, namespaces, lazy-loaded resources, translator integrations, or plugin-based language detection. Its documented resource, fallback, and interpolation features exceed the v1 requirement. |
| Complex messages | Named interpolation plus native formatting | FormatJS / IntlMessageFormat with ICU syntax | Adopt when plural categories, select/gender branches, rich-text messages, or an ICU-based translation workflow become recurring requirements. |
| Catalog delivery | Bundled JavaScript object | Fetched JSON locale files | Adopt fetched catalogs when independent locale deployment or substantial catalog size creates a measured need. |
| Preference source | Explicit selector plus `localStorage` | `navigator.languages` negotiation | Adopt negotiation when product policy supports automatic first-visit locale selection. The v1 product decision specifies English first visit. |

## What Stays Out

| Boundary | Reason | v1 Direction |
|----------|--------|--------------|
| npm, a bundler, a transpiler, or a module loader | The repository ships classic static assets and has no frontend manifest or lockfile. A build pipeline would expand delivery and maintenance scope. | Preserve direct HTML/CSS/JS delivery. |
| i18next or FormatJS runtime packages | Their strongest value appears with multiple maintained locales and complex message grammar. | Use the catalog helper and native `Intl` formatting. |
| CDN-hosted scripts | The admin plane is packaged as a self-contained Docker asset and may run in restricted networks. | Bundle all milestone code in repository assets. |
| Remote catalogs or translation-management integration | v1 ships one complete locale and has no independent translation release process. | Keep catalog data local and versioned with the admin UI. |
| Server-side locale state or API changes | Locale selection is a browser presentation preference. | Keep HTTP, RCON, authentication, and Paper behavior unchanged. |
| Translation of raw Paper, plugin, or RCON output | Those payloads are third-party operational data with plugin-specific vocabulary and formatting. | Translate only admin-authored wrappers and labels. |
| HTML markup inside catalog messages | Markup-bearing translations create escaping, review, and accessibility complexity. | Keep messages as plain text and structure markup in HTML/DOM code. |
| MutationObserver-driven translation | Explicit render paths already own all dynamic UI state. | Reapply static bindings and call deterministic render functions on locale changes. |
| Full framework rewrite | The milestone changes presentation text and locale state. | Retain the existing native application architecture. |
| Intl polyfill bundle | Current browser APIs are broadly available, and the exact deployment browser floor is undocumented. | Feature-detect `Intl.NumberFormat` and fall back to `String(value)`. |

## Stack Patterns by Variant

**For v1 with English as the only complete locale:**

- Keep `LOCALES.en` complete.
- Build the selector from catalog metadata.
- Resolve every unavailable locale or message to English.
- Keep initial HTML copy in English.

**When adding a straightforward second locale:**

- Add one peer catalog with the same key set.
- Permit partial catalog development through English fallback.
- Add key-parity and manual layout checks for longer text.
- Set `lang` and `dir` from locale metadata.

**When complex plural or select grammar becomes common:**

- Evaluate native `Intl.PluralRules` for a small number of local patterns.
- Evaluate FormatJS when ICU messages become a translation-authoring requirement.

**When locale count and delivery complexity grow substantially:**

- Evaluate i18next for namespaces, resource loading, fallback hierarchies, and ecosystem integrations.
- Introduce a package pipeline as a separate architecture decision with lockfile, vendoring, security review, and offline delivery criteria.

## Version and Browser Compatibility

| Capability | Compatibility Position | Codebase Consideration |
|------------|------------------------|------------------------|
| HTML `lang` with BCP 47 tags | Web standard | Use `en` now and exact supported catalog tags later. |
| Native `<select>` | MDN Baseline: widely available | Prefer native behavior over a custom dropdown. |
| `data-*` / `dataset` | MDN Baseline: widely available | Attribute selectors and `getAttribute` also provide a conservative access path. |
| `localStorage` | MDN Baseline: widely available | Catch access errors; remember that scheme, host, and port partition the preference. |
| `Intl.NumberFormat` | MDN Baseline: widely available since September 2017 | Feature-detect because this repository has no documented browser support matrix. |
| Async functions and `fetch` | Existing admin baseline | The i18n helper should avoid introducing newer syntax or APIs such as dynamic import and `replaceAll`. |

The exact oldest supported browser remains an open product constraint. Confidence is HIGH for current desktop browsers and MEDIUM for unusual embedded or legacy Eaglercraft launch environments. The recommended helper can stay within syntax and APIs already used by `admin.js`.

## Verification Gates for the Roadmap

1. **Catalog integrity:** every `data-i18n*` attribute and every literal `t('...')` reference resolves in English; key names are unique; catalog locale metadata uses valid supported tags.
2. **Authored-string audit:** `rg --pcre2 '\p{Han}' web-1.8/admin.html web-1.8/admin.js` returns only reviewed allowlisted data or comments after migration.
3. **Mirror parity:** HTML, JavaScript, and affected CSS remain byte-identical across `web-1.8` and `web-1.12`.
4. **Syntax and regressions:** both scripts pass `node --check` and the existing Python regression suite passes.
5. **Browser smoke:** first visit is English; selector persists after reload; malformed and unsupported stored values resolve to English; blocked storage still leaves a working English UI.
6. **Live switch smoke:** static copy, current dynamic state, dialogs, notifications, title, placeholder, `aria-label`, `lang`, and `dir` update in the active page.
7. **Operational boundary:** raw Paper/plugin/RCON responses are byte-for-byte unchanged in the console; admin-authored errors and wrappers use English catalog entries.
8. **Security boundary:** interpolated player names, server values, and structure data remain escaped at every `innerHTML` sink.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack recommendation | HIGH | Required capabilities map directly to existing browser APIs and the repository has no frontend dependency pipeline. |
| Catalog architecture | HIGH | One complete locale and a single-page classic script favor a flat catalog and small lookup helper. |
| Dependency comparison | HIGH | i18next and FormatJS document the additional fallback, resource, interpolation, and ICU message capabilities that define their later adoption points. |
| Browser compatibility | MEDIUM | Standards support is broad; the project lacks a declared minimum browser matrix and may run in unusual launch environments. |
| Verification approach | HIGH | The repository already uses Node syntax checks, Python standard-library tests, and mirrored assets. |

## Sources

- [WHATWG HTML: the `lang` attribute](https://html.spec.whatwg.org/multipage/dom.html#attr-lang) — verified that document language uses a valid BCP 47 language tag.
- [RFC 5646: Tags for Identifying Languages](https://www.rfc-editor.org/rfc/rfc5646.html) — primary definition for tags such as `en` and future regional variants.
- [WHATWG HTML: Web Storage](https://html.spec.whatwg.org/multipage/webstorage.html) — primary storage model and origin scoping.
- [MDN: `Window.localStorage`](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) — persistence behavior, origin partitioning, and `SecurityError` conditions.
- [MDN: `<select>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/select) — native selector semantics and browser availability.
- [MDN: Using data attributes](https://developer.mozilla.org/en-US/docs/Web/HTML/How_to/Use_data_attributes) — declarative `data-*` binding mechanism and `dataset` access.
- [ECMA-402: NumberFormat Objects](https://tc39.es/ecma402/#numberformat-objects) — primary specification for locale-sensitive numeric formatting.
- [MDN: `Intl.NumberFormat`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat) — practical browser availability and API behavior.
- [WAI-ARIA 1.2: `aria-label`](https://www.w3.org/TR/wai-aria-1.2/#aria-label) — accessible-name semantics for localized labels.
- [i18next configuration: languages, namespaces, resources](https://www.i18next.com/overview/configuration-options#languages-namespaces-resources) — official resource configuration surface.
- [i18next fallback principles](https://www.i18next.com/principles/fallback) — official language and key fallback behavior.
- [i18next interpolation](https://www.i18next.com/translation-function/interpolation) — official named interpolation behavior and escaping model.
- [FormatJS ICU message syntax](https://formatjs.github.io/docs/core-concepts/icu-syntax/) — official plural, select, and rich-text message capabilities.

---
*Stack research for: EaglercraftX admin i18n v1.0*
*Researched: 2026-08-20*
