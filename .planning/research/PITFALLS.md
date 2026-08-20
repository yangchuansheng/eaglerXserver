# Pitfalls Research

**Domain:** Native-browser i18n for the EaglercraftX admin plane
**Researched:** 2026-08-20
**Confidence:** HIGH for codebase findings and browser-platform behavior; MEDIUM for product-policy choices around cross-origin preference sharing and historical console-entry retranslation

## Critical Pitfalls

### Pitfall 1: Treating the HTML text nodes as the complete string inventory

**What goes wrong:**
The initial screen appears English while less-traveled states remain Chinese. Missed strings surface after authentication failure, token expiry, empty player lists, TPS errors, structure searches, configuration saves, server restart, and dialog validation. Attribute values and inline event arguments can remain untranslated even when every obvious heading and button has moved into the locale catalog.

**Why it happens:**
This interface creates text through several channels. `web-1.8/admin.html` contains visible text, `title`, `aria-label`, `placeholder`, and user-facing strings passed through inline `onclick` handlers. `web-1.8/admin.js` writes text through `textContent`, `innerHTML`, `toast()`, `log()`, `setStatus()`, `showActionDialog()`, error handlers, empty states, and timer-driven status refreshes. The mirrored 1.12 files currently contain the same surfaces. A DOM-only inventory sees only the initial markup.

**How to avoid:**
Create a string inventory before changing rendering code. Classify every locally authored string as static text, attribute/accessibility text, status text, dialog text, validation text, notification text, log wrapper, empty/error state, or formatting label. Search both HTML and JavaScript for CJK text and for all UI sinks: `textContent`, `innerHTML`, `setAttribute`, `document.title`, `toast`, `log`, `setStatus`, and dialog configuration objects. Replace inline human-readable handler arguments such as `setTimeValue('0', '日出')` with stable identifiers or message keys. Make English catalog completeness a machine-checked invariant.

**Warning signs:**
- Translation work is estimated from the number of HTML text nodes.
- Inline handlers still carry display labels or success messages.
- A CJK source scan still reports locally authored UI text outside explicit locale fixtures.
- Testing covers only the logged-in happy path.

**Phase to address:**
Phase 1 — Locale contract and inventory. Re-run the inventory as a release gate in Phase 4.

---

### Pitfall 2: Recursive fallback and an incomplete English authority

**What goes wrong:**
A missing key can recurse between the selected locale and English, return `undefined`, render an empty label, or expose an implementation exception. The fallback appears healthy during normal use because common keys exist; a rare error path triggers the failure.

**Why it happens:**
Fallback is often implemented by calling the same translation function with another locale. When English also lacks the key, the function has no terminal state. A permissive API can also hide catalog defects by returning an empty string.

**How to avoid:**
Use a finite lookup with at most two catalog reads: selected locale, then `en`. Validate the requested locale against the catalog first. If both lookups miss, emit one deduplicated diagnostic and return a visible marker such as `[missing:admin.status.offline]`. Keep interpolation after successful lookup. Add a static check asserting that every referenced key exists in English and that English values are non-empty strings.

Recommended contract:

```text
requested locale key -> English key -> visible missing-key marker
```

The English catalog is the schema for every partial locale. Extra keys and missing keys in other locales should be reported separately.

**Warning signs:**
- `t()` calls itself during fallback.
- Unknown locales enter the rendering path.
- Missing English keys become blank text.
- Catalog validation happens only through manual browsing.

**Phase to address:**
Phase 1 — Locale contract and inventory. Verify malformed and intentionally incomplete catalogs in Phase 4.

---

### Pitfall 3: Translating rendered text instead of retaining semantic state

**What goes wrong:**
Changing the selector updates static labels while live state stays in the previous language. Connection status, hero pulse text, world information, player empty states, TPS failures, Seed Map status, structure results, open dialogs, and a currently visible toast can all become stale. The next server refresh may update only part of the screen, producing a mixed-language interface.

**Why it happens:**
Current functions frequently receive or construct final display strings. `setStatus()` stores only text in the DOM. `ACTION_DIALOG` stores a configuration containing concrete labels. Timers can capture translated arrays when they start. Once semantic meaning has been reduced to a string, a locale switch has no reliable way to regenerate it.

**How to avoid:**
Store message keys and interpolation parameters alongside state. Keep `setStatus` state as a stable code such as `online`, `awaitingAuth`, or `offline`; derive visible strings during render. Store dialog field labels, descriptions, validation messages, and confirm text as keys. Tag console entries as either `{kind: 'ui', key, params}` or `{kind: 'raw', text}`. On locale change, update static translations and invoke targeted renderers from existing caches: `WORLD_INFO_CACHE`, `CONFIG_CACHE`, `ONLINE_PLAYERS`, `LAST_STRUCTURE_RESULT`, and current connection/server state. Re-render the open `ACTION_DIALOG` while preserving field values, focus, and pending promise state. Regenerate the visible toast and hero pulse from semantic data.

**Warning signs:**
- Language switching is implemented as a single `[data-i18n]` DOM scan.
- State setters accept final translated sentences.
- Timers close over arrays of translated strings.
- Opening a dialog before switching language leaves its title or validation message unchanged.
- The screen becomes consistent only after a refresh or another server poll.

**Phase to address:**
Phase 3 — Dynamic state and raw-output boundary. Verify live switching under every cached state in Phase 4.

---

### Pitfall 4: Leaving document language and accessible names behind

**What goes wrong:**
Visible text changes while assistive technology still receives Chinese names, the document reports `lang="zh"`, the browser title remains Chinese, placeholders remain Chinese, or icon-only controls expose symbols such as `×` as their accessible name. Screen readers can select the wrong pronunciation rules, and keyboard/screen-reader users encounter a mixed-language control surface.

**Why it happens:**
Accessibility metadata is outside the main visual text flow. The current HTML includes Chinese `lang`, `title`, `aria-label`, and placeholders. `aria-labelledby` references inherit updated visible text, while direct `aria-label` values require explicit updates. Close buttons and status-only regions need deliberate accessible naming.

**How to avoid:**
Include `document.documentElement.lang`, `document.title`, direct `aria-label`, `aria-description` where used, placeholders, input labels, tooltip/title attributes, and icon-button names in the catalog inventory. Use valid BCP 47 language tags. Update metadata in the same synchronous locale-application function as visible text. Preserve `aria-labelledby` relationships and translate their referenced nodes. Add an English `aria-label` to symbol-only close controls. W3C identifies the page language as an accessibility requirement, and WAI guidance treats accessible names as the primary way assistive technology identifies controls.

**Warning signs:**
- Browser accessibility inspection exposes Chinese names after selecting English.
- `<html lang>` changes only after login or a server refresh.
- Placeholders and the browser tab title are absent from the string inventory.
- A close button's computed accessible name is only `×`.

**Phase to address:**
Phase 2 — Static shell and persistence. Audit computed accessible names in Phase 4.

---

### Pitfall 5: Making locale persistence a startup dependency

**What goes wrong:**
A malformed stored value selects a missing catalog, or a `localStorage` exception stops initialization before login and status probing. Users opening the same server through ports 5200 and 5201 see separate preferences and interpret the difference as failed persistence.

**Why it happens:**
Web Storage access can raise `SecurityError`, and storage is scoped to the page origin. Scheme, host, and port participate in origin identity, so `http://host:5200` and `http://host:5201` have independent stores. Stored values also outlive deployments and can reference a locale removed from the current catalog. These behaviors are defined by the browser platform rather than this application.

**How to avoid:**
Use a versioned key such as `eaglerx.admin.locale.v1`. Wrap reads and writes in `try/catch`. Accept a stored value only when it is an own key of the current locale catalog; select English for every invalid or unavailable value. Apply the chosen locale before initializing server-dependent UI. Treat persistence as origin-local for v1 and document/test both exposed origins. Keep the selector functional in memory when storage writes fail.

**Warning signs:**
- Storage is read at top level without exception handling.
- A stored arbitrary string reaches `catalog[locale]`.
- The page fails before `/api/status` after storage is disabled.
- Persistence tests use only one port and one browser state.

**Phase to address:**
Phase 2 — Static shell and persistence. Exercise valid, stale, malformed, and blocked storage in Phase 4.

---

### Pitfall 6: Mixing translation interpolation with HTML construction

**What goes wrong:**
Player names, MOTD text, version/plugin data, structure values, or server messages can break markup or create an injection path when substituted into translated templates assigned through `innerHTML`. Escaping the complete translated result can also turn intended structure into visible markup.

**Why it happens:**
The interface has many `innerHTML` render paths and an existing `escapeHtml()` helper. An i18n helper that returns ready-made HTML makes the trust boundary unclear: catalog text, locally authored markup, and runtime values become one string. MDN describes `innerHTML` as an injection sink; `textContent` inserts plain text without parsing HTML.

**How to avoid:**
Keep catalog values as plain text. Build structure with DOM APIs and assign translated strings and runtime values through `textContent`. Where existing `innerHTML` layouts remain, keep markup in local render code and escape every interpolated value at the final insertion point. Define named interpolation parameters and report missing parameters. Keep rich text as explicit DOM fragments with translated child nodes rather than catalog HTML. Add tests using `<`, `>`, `&`, quotes, braces, and Unicode in every user/server-derived interpolation slot.

**Warning signs:**
- `t()` returns HTML.
- A translated string containing `{player}` is concatenated directly into `innerHTML`.
- Escaping responsibility is split between caller and catalog.
- Tests use only `Steve` and numeric values.

**Phase to address:**
Phase 1 defines the interpolation contract; Phase 3 applies it to dynamic renderers; Phase 4 runs hostile-value checks.

---

### Pitfall 7: Localizing raw Paper, plugin, or RCON output

**What goes wrong:**
Console output is altered, whitespace is normalized, plugin names are translated, or parser inputs change. Operators lose the exact response needed for diagnosis, and the existing player/TPS parsers can fail because localization occurred before extraction.

**Why it happens:**
Raw server output and local UI copy currently meet in the same flows. `send()` logs `d.response`, while fallback wrappers such as `(无输出)` are locally authored. Player and TPS refresh functions parse `d.response` and then create UI. A broad rule such as “pass every displayed string through `t()`” crosses this boundary.

**How to avoid:**
Define an explicit provenance rule. Paper/plugin/RCON response bodies remain opaque strings and flow directly to `log()` via `textContent`. Locally authored wrappers, timestamps, labels, empty-output messages, and request errors use catalog keys. Parse raw responses first; localize only the resulting labels and states. Store raw console entries separately from translatable UI entries so a locale switch can re-render UI messages while preserving raw bytes.

**Warning signs:**
- `t(d.response)` or interpolation receives a complete response body.
- Parsing happens after localized formatting.
- Raw output changes after switching locale.
- Snapshot tests trim or normalize console response bodies.

**Phase to address:**
Phase 3 — Dynamic state and raw-output boundary. Verify byte-preserving output in Phase 4.

---

### Pitfall 8: Leaving locale-sensitive formatting hard-coded

**What goes wrong:**
English labels surround Chinese-formatted numbers, while log timestamps vary with the browser default. The interface has no single active locale even though all catalog strings are English.

**Why it happens:**
`formatNumber()` currently calls `toLocaleString('zh-CN')`, and `log()` calls `toLocaleTimeString()` without the selected locale. String extraction alone does not find these formatting decisions.

**How to avoid:**
Pass the active locale to `Intl.NumberFormat` and `Intl.DateTimeFormat`, or to the existing `toLocale*` calls. Centralize formatter creation per locale and rebuild cached formatters when the locale changes. Keep Minecraft coordinates, command syntax, seed values, version strings, and raw server output semantically unchanged; apply locale formatting only to UI-presentational numbers and times. Define the desired time fields and avoid accidental browser-dependent output.

**Warning signs:**
- `zh-CN` remains in production JavaScript after English migration.
- Locale-sensitive calls omit the active locale.
- Test expectations depend on the developer machine's language.

**Phase to address:**
Phase 3 — Dynamic state and raw-output boundary. Test under at least two browser locales in Phase 4.

---

### Pitfall 9: Allowing the 1.8 and 1.12 admin trees to drift

**What goes wrong:**
One version receives the selector, a fallback fix, or a new message key while the other keeps old behavior. Both pages can pass isolated smoke tests, leaving production behavior dependent on `MINECRAFT_VERSION`.

**Why it happens:**
The project intentionally ships separate `web-1.8/` and `web-1.12/` trees selected by runtime symlink. Their current `admin.html` and `admin.js` files are byte-identical, yet ordinary edits have to be repeated. New locale files add another mirrored surface. Visual review rarely detects catalog-key or error-path differences.

**How to avoid:**
Treat one tree as the editing source during each change, copy the completed admin assets to the other tree, and run byte comparisons before handoff. Gate `admin.html`, `admin.js`, `admin.css`, and every locale/catalog asset. Keep version-specific data in runtime values such as the existing server/version state instead of forking translated source. Add a zero-dependency mirror check to the verification command.

**Warning signs:**
- The same change is manually retyped twice.
- A locale key exists in only one tree.
- Review diffs show semantically similar files with different ordering or whitespace.
- Verification launches only one `MINECRAFT_VERSION`.

**Phase to address:**
All implementation phases preserve the mirror; Phase 4 makes byte equality a release gate.

---

### Pitfall 10: Verifying the default screenshot instead of the state space

**What goes wrong:**
The milestone looks complete in a screenshot and still ships Chinese or stale English in rare states. Missing English keys remain latent because the tested server has players online, healthy TPS, successful authentication, and no open dialogs during switching.

**Why it happens:**
Dynamic admin interfaces have a combinatorial state space. Polling, authentication, dialogs, cache availability, errors, and storage all affect which strings render. Visual happy-path testing covers a small subset.

**How to avoid:**
Combine static checks with a state-transition matrix. Static checks cover referenced keys, English completeness, forbidden legacy literals, locale-aware formatter calls, and mirrored files. Browser checks cover logged out, login prompt, wrong password, authenticated, token expiry, disconnected API, empty and populated player lists, TPS success and failure, world-info loading and failure, configuration success and validation, no-output RCON commands, structure search success/no-result/error, restart/stop confirmation, and a locale switch while every dialog type is open. Inspect visible text, title, `<html lang>`, placeholders, computed accessible names, and raw console output.

**Warning signs:**
- Definition of done says “all visible labels translated.”
- There is no deliberate missing-key test.
- Locale switching is tested only before login.
- Automated checks cannot distinguish raw output from local UI copy.

**Phase to address:**
Phase 4 — Verification and mirror gate, with testability designed into Phases 1–3.

## Technical Debt Patterns

Shortcuts that create expensive follow-up work in this codebase.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store translated sentences in state and caches | Small first diff | Locale switching requires page reload or ad hoc DOM patching | Never for connection state, dialogs, toasts, or cached server panels |
| Use English source text as the key | Fast initial extraction | Copy edits become breaking key migrations; duplicate phrases with different meanings collide | Only for a disposable prototype outside this milestone |
| Put HTML in catalog values | Easy bold/link placement | Injection and escaping rules become ambiguous; translators control structure | Never; use explicit DOM structure |
| Return empty string for missing keys | Clean screenshot | Missing copy becomes invisible and survives review | Never |
| Read `localStorage` without validation | Minimal persistence code | Stale values can break startup after locale changes | Never |
| Translate only future notifications after a switch | Avoids retaining message metadata | Existing dialog, toast, and UI-log content stays stale | Acceptable only if an explicit product policy excludes historical log entries; current visible toast/dialog still requires immediate update |
| Maintain two catalogs manually | No tooling work | Version trees drift silently | Never while the admin assets are intended to remain mirrored |
| Scan only for Chinese characters | Quick legacy check | Misses hard-coded English copy, attributes, and future locales | Useful as one Phase 4 check, never as the sole inventory |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| RCON bridge `/api/rcon` | Localize `d.response` or normalize it before logging/parsing | Preserve response text as opaque data; localize local wrappers after parsing |
| Status/auth APIs | Store the final status sentence returned by a UI helper | Store a state code plus parameters and render it using the active locale |
| Browser Web Storage | Assume one preference spans ports 5200 and 5201 | Treat locale as origin-local, validate values, and continue in memory when storage fails |
| `Intl` formatting | Use `zh-CN` or browser defaults independently of the selector | Derive formatters from the validated active locale |
| Dynmap iframe | Expect the parent locale selector to translate embedded third-party UI | Scope the milestone to the admin shell; preserve Dynmap's own localization behavior |
| `sessionStorage` auth token | Couple language changes to auth initialization or clear login state during rerender | Change locale without replacing the session token or interrupting current API work |
| Mirrored web roots | Test the symlink-selected current version only | Launch and smoke-test both `MINECRAFT_VERSION=1.8` and `1.12`; require byte-equal common admin assets |

## Performance Traps

The interface is small, so correctness dominates. These traps matter because polling and hero timers repeat indefinitely.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full-document translation scans on every player/TPS poll | Repeated DOM work and flicker every 10–20 seconds | Translate static DOM only on locale change; let each dynamic renderer update its own nodes | Immediately visible on lower-end browsers when polling overlaps rendering |
| Rebuilding open dialogs from scratch | Lost input, cursor position, focus, or unresolved promise | Patch translatable nodes or rebuild while snapshotting values/focus and preserving `ACTION_DIALOG` | Any locale switch during a partially completed action |
| Recreating `Intl` formatters for every number/time | Unnecessary allocations in timers and list rendering | Cache one number and time formatter per active locale | Noticeable once repeated player/world rendering grows |
| Logging every missing key on each poll | Console flooding hides real RCON failures | Deduplicate diagnostics by locale and key | First missing key in a timer-driven path |
| Re-rendering raw console history on each locale switch | Large DOM churn and accidental output mutation | Keep raw nodes stable; re-render only locally authored entries that retain keys/params | Long operator sessions with substantial command history |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Interpolating runtime values into catalog HTML | DOM injection through server-derived or operator-controlled values | Plain-text catalog, `textContent`, and escaping at every retained `innerHTML` boundary |
| Treating translated catalog strings as safe code/markup | Future locale additions can alter DOM structure or event behavior | Keep catalog values inert and keep handlers/markup in application code |
| Rendering raw RCON output through `innerHTML` | Plugin output or MOTD content can become executable markup | Keep the existing `log()` text-node behavior for raw bodies |
| Using locale values directly in property paths | Prototype-related property access and unexpected catalog traversal | Validate against an own-property locale registry and use own-property key lookups |
| Exposing secrets through interpolation diagnostics | Missing-parameter logs can print passwords, auth tokens, or full request bodies | Allow only named display parameters and redact security-sensitive values |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Chinese baseline HTML followed by English JavaScript | Visible language flash and incorrect metadata before initialization | Ship English source markup and apply the stored validated locale as early as practical |
| Selector changes only future content | Mixed-language page until refresh/poll | Re-render all visible local UI from semantic state immediately |
| Locale change closes dialogs or clears fields | Lost operator work and uncertainty about command execution | Preserve focus, field values, validation state, and pending action identity |
| Missing key renders blank | Controls appear broken or unnamed | Use English fallback and a fail-visible marker after English miss |
| Raw output and UI wrappers look indistinguishable | Operators cannot tell server text from localized interpretation | Preserve exact raw body and use consistent local timestamp/prefix styling |
| Browser-local persistence is presented as server-wide preference | Different port/browser sessions appear inconsistent | Describe it as this-browser, this-origin preference |
| Language names are translated into the active locale only | Users may struggle to find their language after an accidental switch | Catalog metadata should include a stable native display name; v1 exposes English from catalog metadata |
| Selector lacks a programmatic label | Screen-reader users receive an ambiguous combobox | Pair the native `<select>` with a translated visible label or `aria-label` |

## "Looks Done But Isn't" Checklist

- [ ] **English authority:** Every referenced key exists in `en`, every value is a non-empty string, and unknown keys produce one diagnostic plus a visible marker.
- [ ] **Finite fallback:** An intentionally removed selected-locale key resolves to English; removing the English key terminates without recursion.
- [ ] **Locale validation:** Unknown, stale, inherited-property, and malformed stored values select English safely.
- [ ] **Static text:** Headings, navigation, buttons, notes, table labels, empty states, and footer/terminal controls are catalog-backed or intentionally raw.
- [ ] **Inline handlers:** Human-readable labels and success/error messages are absent from `onclick` arguments.
- [ ] **Dynamic statuses:** Connection, authentication, hero pulse, players, TPS, world information, configuration, Seed Map, and structure search re-render immediately after switching.
- [ ] **Dialogs:** Login, action, restart/stop confirmation, structure overlay, field labels, hints, validation, cancel/confirm text, and current error state switch in place without losing input or focus.
- [ ] **Notifications:** Visible toast and locally authored console entries follow the selected locale according to the documented history policy.
- [ ] **Raw output:** Paper/plugin/RCON response bodies remain byte-for-byte unchanged before and after locale switching.
- [ ] **No-output boundary:** The local `(no output)` wrapper translates while the raw response path stays opaque.
- [ ] **Document metadata:** `<html lang>`, browser title, placeholders, tooltip/title text, and direct ARIA strings update synchronously.
- [ ] **Accessible names:** Every icon/symbol-only control has a meaningful computed accessible name in English.
- [ ] **Formatting:** Number and time formatting use the active locale; command syntax, coordinates, seeds, versions, and raw server text retain their operational form.
- [ ] **Persistence:** Refresh restores the selected valid locale on the same origin. Blocked storage leaves the page operational. Ports 5200 and 5201 are tested as separate origins.
- [ ] **First paint:** English source markup prevents a Chinese-to-English flash and reports `lang="en"` before application initialization.
- [ ] **Escaping:** Interpolation tests cover markup characters, quotes, braces, ampersands, Unicode, MOTD text, and server-derived values.
- [ ] **Error matrix:** Wrong password, token expiry, network failure, HTTP error, malformed response, empty players, TPS failure, world-info failure, no structure result, and restart failure contain no legacy local UI strings.
- [ ] **Source scan:** Locally authored Chinese UI literals are absent from admin HTML/JS/CSS outside explicit locale data; UI sink review catches hard-coded English additions too.
- [ ] **Syntax and smoke:** `node --check` passes for both JavaScript files, and browser smoke tests pass for both server versions.
- [ ] **Mirror gate:** `admin.html`, `admin.js`, `admin.css`, and every locale/catalog asset are byte-identical between `web-1.8` and `web-1.12`.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Missed strings discovered late | MEDIUM | Add the missed sink/state to the inventory, introduce stable keys, add a regression state to the matrix, and scan both trees |
| Fallback loop or blank English key | LOW | Replace recursion with bounded lookup, restore the English key, add completeness and deliberate-miss checks |
| Stale dynamic DOM after switch | HIGH | Identify the missing semantic state, retain key/params, add a targeted renderer, and verify switching during that state |
| Accessibility metadata left behind | LOW | Extend locale application to document/attribute nodes and audit computed names with browser accessibility tools |
| Storage blocks startup | LOW | Catch storage access, validate the value, select English in memory, and retest denied storage |
| Unsafe HTML interpolation | HIGH | Move variables to `textContent` or escape at the final HTML boundary, then test adversarial values across every sink |
| Raw RCON output altered | HIGH | Split raw and UI message types, restore raw text-node rendering, and add exact-output snapshots before parser/localization stages |
| Locale formatting inconsistency | LOW | Centralize active-locale formatters and remove hard-coded/default-locale calls |
| Mirrored tree drift | MEDIUM | Choose the intended version, copy common assets to its pair, review the resulting diff, and add byte-comparison gating |
| Apparent completeness with rare-state gaps | MEDIUM | Reproduce the missed state, add it to the state-transition matrix, and link its keys to English completeness checks |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Incomplete string inventory | Phase 1 — Locale contract and inventory | CJK scan plus UI-sink/key-reference audit; every category has an owner and English key |
| Recursive fallback / incomplete English | Phase 1 — Locale contract and inventory | Selected-locale miss falls back once; English miss returns a marker; completeness check fails the build/check |
| Unsafe interpolation contract | Phase 1, enforced in Phase 3 | Catalog contains plain text; hostile values remain text in all dynamic renderers |
| Metadata and accessible-name gaps | Phase 2 — Static shell and persistence | Inspect `<html lang>`, title, placeholders, ARIA, and computed names after load and switch |
| Storage startup failures and origin confusion | Phase 2 — Static shell and persistence | Test fresh/valid/stale/malformed/blocked storage on ports 5200 and 5201 |
| Stale dynamic state | Phase 3 — Dynamic state and raw-output boundary | Switch locale during every live state and open dialog; values/focus/pending action survive |
| Raw server output mutation | Phase 3 — Dynamic state and raw-output boundary | Exact raw response fixture matches displayed/stored body before and after locale change |
| Hard-coded locale formatting | Phase 3 — Dynamic state and raw-output boundary | Run with different browser defaults; UI time/number output follows selected locale |
| Version-tree drift | Phase 4 — Verification and mirror gate | Byte comparisons pass for all common admin and locale assets |
| Screenshot-only completion | Phase 4 — Verification and mirror gate | Full logged-out/authenticated/error/dialog/state matrix passes for 1.8 and 1.12 |

### Recommended phase exit criteria

1. **Phase 1 exits** when the English catalog is the validated key schema, fallback is bounded and fail-visible, interpolation rules are explicit, and every current UI sink has been inventoried.
2. **Phase 2 exits** when English is correct from first paint, the native selector updates document/accessibility metadata, locale persistence survives invalid or unavailable storage, and auth initialization remains intact.
3. **Phase 3 exits** when all current and cached dynamic states re-render from keys/parameters, active-locale formatting is centralized, operator input survives switches, and raw server responses remain opaque.
4. **Phase 4 exits** when static checks and the state-transition matrix pass for both Minecraft versions, accessibility metadata is inspected, hostile interpolation fixtures remain inert, and common admin assets are byte-identical across both web trees.

## Sources

### Codebase evidence

- `.planning/PROJECT.md` — milestone scope, native-stack constraints, English fallback, persistence, mirrored versions, and raw-output requirement.
- `.planning/codebase/ARCHITECTURE.md` — runtime selection, admin-plane boundaries, HTTP/RCON flow, and version topology.
- `.planning/codebase/STRUCTURE.md` — mirrored web roots and admin asset locations.
- `.planning/codebase/CONVENTIONS.md` — current implementation conventions and mirroring expectations.
- `.planning/codebase/TESTING.md` — available verification practices and current test constraints.
- `web-1.8/admin.html`, `web-1.12/admin.html` — static text, attributes, inline handler strings, dialogs, and accessibility surfaces; files were byte-identical when researched.
- `web-1.8/admin.js`, `web-1.12/admin.js` — dynamic UI sinks, caches, raw RCON logging, parser boundaries, formatting calls, dialogs, timers, and error states; files were byte-identical when researched.

### Official platform and accessibility guidance

- [MDN: Window.localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) — origin-scoped persistence and `SecurityError` behavior.
- [MDN: Same-origin policy / origin definition](https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy#definition_of_an_origin) — scheme/host/port origin identity.
- [MDN: Node.textContent](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent) — plain-text DOM insertion behavior.
- [MDN: Element.innerHTML](https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML) — injection-sink warning and HTML parsing behavior.
- [MDN: Number.prototype.toLocaleString](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/toLocaleString) — locale-sensitive number formatting and formatter reuse guidance.
- [MDN: Date.prototype.toLocaleTimeString](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/toLocaleTimeString) — locale-sensitive time formatting.
- [W3C WAI: Understanding SC 3.1.1 Language of Page](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html) — declaring the page's default human language for accessibility.
- [W3C WAI-ARIA APG: Providing Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) — accessible-name behavior for controls and labeling techniques.
- [W3C Internationalization: Choosing a Language Tag](https://www.w3.org/International/questions/qa-choosing-language-tags) — valid BCP 47 language-tag selection.

---
*Pitfalls research for: EaglercraftX Admin i18n v1.0*
*Researched: 2026-08-20*
