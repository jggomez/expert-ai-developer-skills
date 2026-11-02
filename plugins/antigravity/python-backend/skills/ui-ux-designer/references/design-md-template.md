---
name: "Project Design System"
version: "1.0.0"
colors:
  primary: "#0D6EFD"
  primary_hover: "#0B5ED7"
  secondary: "#6C757D"
  surface: "#FFFFFF"
  surface_alt: "#F8F9FA"
  surface_dark: "#121212"
  text: "#212529"
  text_muted: "#6C757D"
  border: "#DEE2E6"
  success: "#198754"
  warning: "#B76E00"
  error: "#DC3545"
typography:
  font_sans: "Inter, system-ui, -apple-system, sans-serif"
  font_mono: "JetBrains Mono, Fira Code, monospace"
  scale:
    display: "2.25rem/1.2"
    h1: "1.875rem/1.25"
    h2: "1.5rem/1.33"
    body: "1rem/1.5"
    caption: "0.75rem/1.33"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button_primary:
    background: "{colors.primary}"
    hover_background: "{colors.primary_hover}"
    color: "{colors.surface}"
    radius: "{rounded.md}"
    padding: "{spacing.sm} {spacing.md}"
  input:
    background: "{colors.surface}"
    color: "{colors.text}"
    border: "1px solid {colors.border}"
    error_border: "1px solid {colors.error}"
    radius: "{rounded.md}"
  card:
    background: "{colors.surface_alt}"
    border: "1px solid {colors.border}"
    radius: "{rounded.lg}"
    padding: "{spacing.lg}"
---

# DESIGN.md — [Project Name]

## Overview
Clarity-first, accessible design system built on semantic tokens, predictable visual feedback, and WCAG 2.1 AA contrast (`>= 4.5:1` for text, `>= 3:1` for UI controls). Compatible with `npx @google/design.md lint DESIGN.md` and Google Stitch MCP.

## Colors
Use semantic tokens exclusively (`{colors.primary}`, `{colors.surface}`, `{colors.text}`, `{colors.error}`). Pair light surfaces (`#FFFFFF` / `#F8F9FA`) with dark text (`#212529`) and invert cleanly in dark mode (`{colors.surface_dark}` `#121212` with `#F8F9FA` foreground). Never convey status by color alone.

## Typography
Primary UI uses `font_sans` (`Inter`); code, IDs, and tabular metrics use `font_mono` (`JetBrains Mono`). Scale progresses from `caption` (`0.75rem`) and `body` (`1rem`) to `h2` (`1.5rem`), `h1` (`1.875rem`), and `display` (`2.25rem`). Use relative `rem` units to respect OS font scaling.

## Layout
8pt/4pt spacing rhythm (`xs: 4px`, `sm: 8px`, `md: 16px`, `lg: 24px`, `xl: 32px`). Responsive grid breakpoints: Mobile `< 640px` (4 cols, `16px` margin), Tablet `768px–1023px` (8–12 cols, `24px` margin), Desktop `>= 1024px` (12 cols, max `1280px` container). Zero horizontal overflow.

## Elevation & Depth
Flat borders (`1px solid {colors.border}`) separate peer surfaces; subtle elevation shadows (`0 4px 12px rgba(0,0,0,0.08)`) are reserved for interactive cards, popovers, sticky headers, and modal overlays.

## Shapes
Consistent corner geometry via `{rounded.sm}` (`4px` badges/tags), `{rounded.md}` (`8px` buttons/inputs), `{rounded.lg}` (`12px` cards/dialogs), and `{rounded.full}` (`9999px` pills/avatars).

## Components
Every interactive atom (`button_primary`, `input`, `card`, navigation items) must implement all states: `default`, `hover`, `focus-visible` (`2px solid {colors.primary}` offset `2px`), `active`, `disabled` (`opacity: 0.5`), `loading` (fixed-width inline spinner), `empty`, and `error` (`{colors.error}` border + helper message).

## Do's and Don'ts
- **Do**: Reference YAML tokens (`{colors.primary}`, `{spacing.md}`), preserve visible input labels, enforce touch targets (`>= 44x44pt` iOS / `48x48dp` Android / `40px` Web), and honor `prefers-reduced-motion`.
- **Don't**: Hardcode raw hex values or magic pixel padding in components, strip `:focus-visible` outlines (`outline: none`), or omit empty/loading/error states on async views.
