# Roadmap: EaglercraftX 1.8 Server

## Overview

Milestone v1.0 delivers complete English and Simplified Chinese (`zh-CN`) experiences for the browser administration plane, with English as the first-visit default and primary fallback: first define the bilingual locale contract, then localize the static shell and preference, migrate stateful renderers while protecting operational output, and finally prove mirrored behavior across both web roots.

## Phases

- [x] **Phase 1: Locale Contract and Inventory** - Establish complete English and `zh-CN` catalogs, safe locale runtime, and semantic message inventory. (completed 2026-08-20)
- [ ] **Phase 2: Bilingual Static Shell and Preference** - Deliver English first paint, persistent locale choice, immediate switching, and localized static accessibility surfaces.
- [ ] **Phase 3: Dynamic Renderers and Raw-Output Boundary** - Localize stateful UI while preserving operator context and exact server-originated output.
- [ ] **Phase 4: Mirror Gate and Release Matrix** - Prove parity, catalog integrity, and end-to-end administration flows in both web roots.

## Phase Details

### Phase 1: Locale Contract and Inventory

**Goal**: Operators have a reliable bilingual locale foundation whose messages are safe, diagnosable, and separate from operational values.
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, SAFE-03
**Success Criteria** (what must be TRUE):

  1. Every inventoried client-authored interface message has reviewed English and `zh-CN` catalog entries that the locale runtime can resolve.
  2. A missing active-locale value resolves to English, while an absent English key appears as a visible marker and produces one console diagnostic.
  3. Client-authored messages can show named values as plain text without interpreting catalog or interpolation content as markup.
  4. The locale registry exposes `en` and `zh-CN` through one stable contract that future catalogs can join, and localized display labels leave command arguments, configuration enums, and protocol values unchanged.

**Plans**: 4/4 complete
**UI hint**: yes

### Phase 2: Bilingual Static Shell and Preference

**Goal**: Operators open an English administration shell, switch immediately to `zh-CN`, and retain a valid language choice across browser sessions.
**Depends on**: Phase 1
**Requirements**: PREF-01, PREF-02, PREF-03, PREF-04, COVR-01, COVR-05
**Success Criteria** (what must be TRUE):

  1. A first-time visitor sees the administration shell in English before signing in.
  2. The always-visible header selector lists `English` and `简体中文`, applies a valid choice immediately, and restores that choice on a later visit to the same origin.
  3. Missing, stale, invalid, or unavailable stored preferences open the interface in English without preventing administration.
  4. Static navigation, headings, labels, buttons, hints, and empty states resolve through translation keys in both bundled locales.
  5. The active locale updates the document language and title plus UI-owned titles, iframe title, form labels, placeholders, and ARIA text.

**Plans**: 2/2 plans executed

- [x] 02-01-PLAN.md
- [x] 02-02-PLAN.md

**UI hint**: yes

### Phase 3: Dynamic Renderers and Raw-Output Boundary

**Goal**: Operators receive localized client-owned feedback without losing live administration context or altering server evidence.
**Depends on**: Phase 2
**Requirements**: COVR-02, COVR-03, COVR-04, COVR-06, SAFE-01, SAFE-02, SAFE-04
**Success Criteria** (what must be TRUE):

  1. Authentication, status, player, world, TPS, and configuration views render their client-authored messages through translation keys.
  2. Dialogs, loading states, toasts, success messages, warnings, and client-authored errors use localized titles, descriptions, fields, placeholders, validation, and actions.
  3. Locale changes retain authentication, entered values, selections, focus, open dialogs, and cached server data while localized views refresh from existing client state.
  4. Locale changes retain polling and server-operation state without introducing duplicate requests or timers, and UI-owned numbers and dates follow the active locale's native formatting.
  5. Paper, plugin, and RCON response content remains byte-for-byte unchanged when displayed in the administration interface.

**Plans**: TBD
**UI hint**: yes

### Phase 4: Mirror Gate and Release Matrix

**Goal**: Operators can rely on the same localized administration experience across the 1.8 and 1.12 web distributions.
**Depends on**: Phase 3
**Requirements**: PARI-01, PARI-02, PARI-03
**Success Criteria** (what must be TRUE):

  1. Both web roots expose identical locale identifiers, catalog keys, fallback behavior, and locale interactions.
  2. Automated release checks verify English-key coverage, referenced-key integrity, and equality of mirrored administration assets.
  3. Browser acceptance demonstrates authentication, player, world, configuration, dialog, notification, command, and error flows for both web versions.

**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Locale Contract and Inventory | 4/4 | Complete    | 2026-08-20 |
| 2. English-First Static Shell and Preference | 2/2 | In Progress|  |
| 3. Dynamic Renderers and Raw-Output Boundary | 0/TBD | Not started | - |
| 4. Mirror Gate and Release Matrix | 0/TBD | Not started | - |
