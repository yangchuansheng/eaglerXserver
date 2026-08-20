# EaglercraftX 1.8 Server

## What This Is

EaglercraftX 1.8 Server packages Paper 1.8.8 and Paper 1.12.2, Waterfall, browser clients, and an authenticated browser administration plane into one Docker image. Operators select one Minecraft version per container and manage server state, players, worlds, configuration, and diagnostics from the admin interface.

## Core Value

Operators can reliably run either supported server version and administer it through one browser-based control plane.

## Requirements

### Validated

- ✓ A single image contains both Paper 1.8.8 and Paper 1.12.2 runtimes and selects one through the required `MINECRAFT_VERSION` setting.
- ✓ The Waterfall WebSocket entry point and HTTP client service are available on port 5200.
- ✓ The management service exposes authenticated RCON operations, status, Dynmap proxying, and static fallback service on port 5201.
- ✓ The admin interface supports server, player, world, gameplay, configuration, and diagnostic operations.
- ✓ The 1.8 and 1.12 web trees provide matching admin interface assets.

### Active

- [ ] Make English the complete default locale for every admin-authored interface string.
- [ ] Provide an extensible client-side locale catalog and English fallback behavior.
- [ ] Add a header language selector that persists the selected locale in `localStorage`.
- [ ] Route static text, dynamic status text, dialogs, notifications, titles, and accessibility labels through translation keys.
- [ ] Keep the 1.8 and 1.12 admin implementations and locale keys synchronized.

### Out of Scope

- A second complete locale catalog — deferred until the i18n foundation is verified.
- Translation of raw Paper, plugin, and RCON command output — server-originated text remains unchanged.
- Remote translation management or runtime catalog downloads — bundled static catalogs cover the current deployment model.

## Current Milestone: v1.0 Admin i18n

**Goal:** Make English the default admin language and establish an extensible, dependency-free localization foundation.

**Target features:**
- Complete English locale and fallback behavior
- Persistent header language selector
- Translation coverage for static, dynamic, dialog, notification, title, and accessibility text
- Mirrored behavior across the 1.8 and 1.12 admin assets

## Context

- The current admin interface embeds Simplified Chinese strings directly in both HTML and JavaScript.
- `web-1.8/admin.*` and `web-1.12/admin.*` are maintained as matching copies and currently contain an in-progress visual redesign in the working tree.
- The browser interface uses plain HTML, CSS, and JavaScript without a bundler, module loader, or client framework.
- Existing management APIs and raw server responses already define the operational behavior; this milestone changes presentation and locale selection only.

## Constraints

- **Compatibility**: Preserve admin behavior for both Minecraft versions — both web trees ship in the same image.
- **Dependencies**: Use existing browser APIs and plain JavaScript — the project has no frontend dependency pipeline.
- **Default locale**: English is used on first visit and whenever a translation key is missing — this is the milestone's primary user-facing outcome.
- **Persistence**: Store locale preference in `localStorage` — operators retain their choice across browser sessions.
- **Accessibility**: Localize document language, titles, labels, placeholders, and ARIA text together with visible text.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Ship English as the only complete locale in v1.0 | Establish and verify the localization mechanism before maintaining additional catalogs | — Pending |
| Use a header selector with `localStorage` persistence | Keeps language choice explicit and durable while preserving English for first visits | — Pending |
| Use English as the fallback locale | Guarantees complete, deterministic interface text when catalogs are incomplete | — Pending |
| Keep server-originated command output in its source language | Raw output is controlled by Paper and plugins and may contain dynamic third-party text | — Pending |
| Add no frontend dependency | Native browser APIs cover catalogs, DOM updates, and preference storage | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-20 after starting milestone v1.0 Admin i18n*
