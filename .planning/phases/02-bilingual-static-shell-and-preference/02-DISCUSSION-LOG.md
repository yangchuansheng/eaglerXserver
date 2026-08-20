# Phase 2: Bilingual Static Shell and Preference - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents. Decisions are captured in `02-CONTEXT.md`; this log preserves the alternatives considered.

**Date:** 2026-08-20
**Phase:** 2-bilingual-static-shell-and-preference
**Mode:** Generic-agent workaround; autonomous `--auto`
**Areas discussed:** static shell wiring, first-paint locale behavior, selector structure, preference recovery, DOM attributes and accessibility, state-preserving switching boundary

---

## Static shell wiring

| Option | Description | Selected |
|--------|-------------|----------|
| English source copy with explicit static bindings | Keep usable English HTML and attach catalog keys to static text and attributes. | ✓ |
| Runtime-populated shell | Build visible shell copy only after JavaScript initialization. | |
| Global DOM translation scan | Find translatable content through document-wide scanning. | |

**User's choice:** `[auto]` Recommended default selected: English source copy with explicit static bindings.
**Notes:** It preserves the static deployment model, supplies a usable fallback shell, and makes every translated surface reviewable beside its DOM target.

---

## First-paint locale behavior

| Option | Description | Selected |
|--------|-------------|----------|
| English first paint with synchronous preference application | Author English in HTML; resolve a stored valid locale before `init()` starts administration requests. | ✓ |
| Browser-language negotiation | Choose the initial locale from browser language preferences. | |
| Blank shell until locale initialization | Delay visible shell copy until runtime setup finishes. | |

**User's choice:** `[auto]` Recommended default selected: English first paint with synchronous preference application.
**Notes:** The v1 policy fixes English as first visit and primary fallback. A valid stored preference applies before the existing async status startup.

---

## Selector structure

| Option | Description | Selected |
|--------|-------------|----------|
| Native header select from registry metadata | Add an always-visible `<select>` to the header and derive options from `EaglerXI18n.locales`. | ✓ |
| Custom menu | Build an application-specific popover control. | |
| Settings-only control | Place the locale choice inside a later configuration surface. | |

**User's choice:** `[auto]` Recommended default selected: native header select from registry metadata.
**Notes:** Native controls provide keyboard behavior and a label association through the existing dependency-free page model.

---

## Preference recovery

| Option | Description | Selected |
|--------|-------------|----------|
| Validated localStorage with English recovery | Guard storage access, validate an own locale ID, and use English when recovery is needed. | ✓ |
| Trust any stored string | Feed stored data directly to the runtime. | |
| Server-side preference | Persist the choice through an administration API. | |

**User's choice:** `[auto]` Recommended default selected: validated localStorage with English recovery.
**Notes:** `eaglerx_admin_locale` stays origin-scoped. A storage-write failure retains the valid current-session selection.

---

## DOM attributes and accessibility

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit semantic text and attribute bindings | Bind static text plus document metadata, titles, placeholders, iframe title, and ARIA names through catalog keys. | ✓ |
| Visible labels only | Limit Phase 2 to rendered text nodes. | |
| Accessibility follow-up | Defer metadata and accessible names to a later phase. | |

**User's choice:** `[auto]` Recommended default selected: explicit semantic text and attribute bindings.
**Notes:** Attribute values use dedicated `data-i18n-*` declarations. Structural reference values such as `for`, IDs, and `aria-labelledby` remain stable.

---

## State-preserving switching boundary

| Option | Description | Selected |
|--------|-------------|----------|
| In-place static refresh with preserved runtime state | Update static DOM and metadata while retaining the current administration runtime and state holders. | ✓ |
| Page reload | Reload after every locale choice. | |
| Full dynamic rerender in Phase 2 | Localize stateful renderers, dialogs, and feedback during static-shell work. | |

**User's choice:** `[auto]` Recommended default selected: in-place static refresh with preserved runtime state.
**Notes:** The handler performs no request, command, timer creation, or initialization. Phase 3 owns dynamic renderer and dialog localization from existing state.

---

## the agent's Discretion

- Helper names and the smallest classic-browser implementation for static binding application.
- Exact existing semantic keys for static targets.
- Compact CSS declaration details within protected header breakpoints and focus styling.
- Standard-library test placement and assertions for static bindings, preference recovery, and mirror parity.

## Deferred Ideas

- Dynamic renderers, dialogs, toasts, terminal history, polling presentation, and raw-output framing belong to Phase 3.
- Browser acceptance and release parity proof across both web roots belong to Phase 4.
- Additional locales and browser-language negotiation remain outside v1.0.
