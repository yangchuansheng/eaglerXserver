# Design System Specification: Supabase-Inspired Server Console

This document defines the visual language, design tokens, and component architecture for the **EaglercraftX Admin Console**, adapted from the **Supabase** design system documented in [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md/tree/main/design-md/supabase/DESIGN.md).

---

## 1. Visual Theme & Atmosphere

- **Aesthetic**: Technical, developer-first cloud console. Dark-first canvas with the signature Supabase emerald green (`#3ECF8E`) as the primary operational CTA and status indicator.
- **Philosophy**: Clean, high-density server administration interface. Every element serves an operational purpose. Eliminates visual clutter, unnecessary decorative gradients, and amateur AI-slop clichés (no fake purple-cyan glows, no arbitrary 01/02 labels, no nested cards inside cards).
- **Surface Hierarchy**:
  - `Canvas (Root)`: `#0e1011` / `#121212` (deep dark foundation)
  - `Surface 1 (Header, Sidebar, Drawer)`: `#171717` (clean dark chrome with `1px` border)
  - `Surface 2 (Cards, Panels, Tables)`: `#1a1a1a` (subtle contrast against canvas)
  - `Surface 3 (Inputs, Code blocks, Inner tiles)`: `#141414` / `#222222`
  - `Hairline Borders`: `rgba(255, 255, 255, 0.08)` / `#262626`
  - `Hairline Strong`: `rgba(255, 255, 255, 0.16)` / `#333333`

---

## 2. Color Palette & Roles

| Semantic Token | Hex / Value | Usage |
|---|---|---|
| `--color-primary` | `#3ECF8E` | Signature Supabase Emerald. Primary CTAs, active status, success badges |
| `--color-primary-hover` | `#4ade80` | Hover state for emerald buttons and interactive highlights |
| `--color-primary-deep` | `#24b47e` | Active / pressed state for primary CTAs |
| `--color-primary-faint` | `rgba(62, 207, 142, 0.12)` | Subtle emerald badge / active navigation background |
| `--color-on-primary` | `#0d1712` | Near-black text on emerald background (Supabase signature style) |
| `--color-canvas` | `#0e1011` | Application base background |
| `--color-surface-1` | `#161616` | Header, sidebar, and elevated navigation bars |
| `--color-surface-2` | `#1c1c1c` | Cards, panels, workspace section containers |
| `--color-surface-3` | `#222222` | Form controls, button secondary backgrounds, code blocks |
| `--color-border` | `rgba(255, 255, 255, 0.08)` | Standard hairline divider and card border |
| `--color-border-strong` | `rgba(255, 255, 255, 0.16)` | Focused inputs, hovered cards, active tab borders |
| `--color-text` | `#ededed` | Primary high-contrast text |
| `--color-text-secondary`| `#a0a0a0` | Secondary descriptions, subtitles, table headers |
| `--color-text-muted` | `#6e6e6e` | Placeholders, timestamps, disabled indicators |
| `--color-danger` | `#f87171` | Destructive actions (Guanfu/Stop, Ban, Kick) |
| `--color-danger-bg` | `rgba(248, 113, 113, 0.12)` | Danger button background and alert fill |
| `--color-warning` | `#fbbf24` | Authentication pending, reload notices, TPS warning |
| `--color-info` | `#60a5fa` | Version tags, external link pills, informational notices |

---

## 3. Typography Rules

- **Display & Interface Font**:
  ```css
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  ```
- **Monospace & Data Font**:
  ```css
  font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, "Liberation Mono", monospace;
  font-variant-numeric: tabular-nums;
  ```
- **Hierarchy Scale**:
  - `Header Title`: 15px, weight 600, letter-spacing -0.01em
  - `Section Heading`: 17px, weight 600, letter-spacing -0.02em
  - `Card Title`: 13px, weight 600, text-transform none, letter-spacing -0.01em
  - `Body Text`: 13px, weight 400, line-height 1.5
  - `Button Label`: 13px, weight 500, letter-spacing 0, `white-space: nowrap`
  - `Badge / Pill / Monospace`: 11px - 12px, weight 500, tabular-nums

---

## 4. Component Stylings

### 4.1 Buttons
- **Primary CTA (`.btn-ok`, `#cmd-bar button`, primary buttons)**:
  - Background: `var(--color-primary)` (`#3ECF8E`)
  - Text: `var(--color-on-primary)` (`#0d1712`)
  - Border: `1px solid var(--color-primary-deep)`
  - Border-Radius: `6px` (`rounded.sm`)
  - Padding: `6px 14px`
  - Hover: Background `#4ade80`, subtle lift
- **Secondary / Action Buttons (`.qbtns button`, `.btn-cancel`)**:
  - Background: `#222222`
  - Text: `#ededed`
  - Border: `1px solid rgba(255, 255, 255, 0.1)`
  - Border-Radius: `6px`
  - Padding: `6px 12px`
  - Hover: Background `#2c2c2c`, Border `rgba(255, 255, 255, 0.2)`
- **Danger Button (`.danger-btn`)**:
  - Background: `rgba(248, 113, 113, 0.1)`
  - Text: `#fca5a5`
  - Border: `1px solid rgba(248, 113, 113, 0.25)`
  - Border-Radius: `6px`
  - Hover: Background `rgba(248, 113, 113, 0.2)`, Border `#f87171`

### 4.2 Toggles & Form Controls
- **Toggle Switch (`.toggle`)**:
  - Track: `36px × 20px`, border-radius `9999px`, background `#2c2c2c`, border `1px solid rgba(255,255,255,0.12)`.
  - Thumb: `14px × 14px`, border-radius `50%`, background `#888888`.
  - Checked State: Track background `#3ECF8E`, Thumb background `#0d1712`, thumb translated `16px`.
- **Inputs (`input`, `select`)**:
  - Background: `#141414`
  - Border: `1px solid rgba(255, 255, 255, 0.12)`
  - Border-Radius: `6px`
  - Text: `#ededed`
  - Focus: Border `var(--color-primary)`, box-shadow `0 0 0 2px rgba(62, 207, 142, 0.2)`

### 4.3 Navigation & Sidebar
- **Sidebar (`.control-nav`)**:
  - Compact width `220px`, sticky desktop positioning.
  - Links have clean SVG icons, high-legibility text, and active indicators using emerald accent pill styling.
  - No cheese numbers (01, 02...).

### 4.4 Terminal Console Drawer (`.console-drawer`)
- Embedded developer terminal dock inspired by Supabase SQL Editor and Warp Terminal.
- Crisp syntax coloring for Paper / Bukkit / Minecraft console messages.
- Command prompt input with `/` glyph and keyboard navigation (Enter).

### 4.5 Modals & Dialogs
- Centered overlays with backdrop blur `8px` and dark tint `rgba(0, 0, 0, 0.65)`.
- Dialog box: `#1a1a1a`, border `1px solid rgba(255, 255, 255, 0.12)`, radius `10px`, shadow `0 20px 48px rgba(0, 0, 0, 0.6)`.

---

## 5. Do's and Don'ts

### Do:
- Keep the signature `#3ECF8E` emerald scarce and meaningful (primary actions, online status, active triggers).
- Maintain crisp `6px` border-radii for buttons and inputs.
- Use tabular numbers for TPS, player counts, memory, and coordinates.
- Preserve 100% of functional DOM IDs, event handlers, and data-i18n keys for bilingual localization.

### Don't:
- Do NOT use purple-to-blue gradient backgrounds or rainbow text.
- Do NOT add arbitrary numbered section badges (01, 02, 03).
- Do NOT make buttons pill-shaped (except for tags and status chips).
- Do NOT use low-contrast gray text on colored backgrounds.
