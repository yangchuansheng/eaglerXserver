# Admin Console UI Contract

This document records the durable UI constraints for the EaglercraftX admin console. Concrete colors, spacing, and component values live in `web-1.8/admin.css` and `web-1.12/admin.css` as the single source of truth.

## Runtime boundaries

- `script/http_server.py` is the production management backend and static-file fallback.
- The management page loads scripts, styles, and images from the selected local web root and uses native system font stacks.
- Explicit user actions may open external tools such as Seed Map in a new tab.
- The 1.8 and 1.12 admin assets remain byte-identical release artifacts.

## Compatibility

- Preserve functional DOM IDs, inline handlers, and `data-i18n*` bindings.
- Update JavaScript, both locale catalogs, and the compact source-coverage contract in `tests/test_regressions.py` together when a binding changes.
- Preserve keyboard navigation, focus visibility, semantic labels, and 44px touch targets on narrow viewports.
- Keep the console usable from 320px mobile layouts through desktop widths without horizontal page overflow.

## Visual principles

- Use a dark neutral canvas, flat surfaces, hairline borders, and compact 6px to 8px radii.
- Reserve emerald for primary actions, active navigation, and healthy status.
- Use warning and danger colors only for their matching operational states.
- Use system sans-serif and monospace stacks with tabular numerals for server data.
- Keep the overview limited to connection state, online player count, and TPS.
- Keep one clear surface per operational group and concise copy around controls.

## Interaction principles

- Native anchors handle section navigation; the scroll observer only updates the active navigation item.
- Status values render from API state through the existing localization layer.
- Dialogs collect parameters for real management commands and retain their current validation paths.
- Motion communicates state changes such as authentication, dialogs, and toasts.
