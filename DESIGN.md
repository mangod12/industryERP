# KBSteel ERP — Design System

## Color Strategy: Committed
One primary color carries identity. Steel-blue as the anchor, warm neutrals for the environment.

### Palette (OKLCH)
- **Primary:** oklch(45% 0.15 250) — deep steel blue, used for nav, buttons, active states
- **Primary Light:** oklch(92% 0.03 250) — tinted background for cards, hover states
- **Accent:** oklch(65% 0.18 145) — green for success, completed, approved states
- **Warning:** oklch(75% 0.15 75) — amber for pending, in-progress
- **Danger:** oklch(55% 0.2 25) — red for rejected, errors, alerts, scrap
- **Surface:** oklch(97% 0.005 250) — off-white with steel tint, main background
- **Surface Raised:** oklch(99% 0.003 250) — cards, panels
- **Text Primary:** oklch(25% 0.01 250) — near-black with warmth
- **Text Secondary:** oklch(50% 0.01 250) — labels, metadata
- **Border:** oklch(88% 0.01 250) — subtle separation

### Stage Colors
- Fabrication: oklch(60% 0.15 250) — blue
- Painting: oklch(70% 0.15 75) — amber
- Dispatch: #0b4f86 on #eef6ff - steel blue
- Completed: oklch(60% 0.18 145) — green

## Typography
- **Font Stack:** system-ui, -apple-system, "Segoe UI", Roboto, sans-serif
- **Heading Font:** Inter (loaded via Google Fonts) or system fallback
- **Mono:** "JetBrains Mono", "Fira Code", ui-monospace (for weights, quantities, codes)
- **Scale:** 0.75rem / 0.875rem / 1rem / 1.25rem / 1.5rem / 2rem
- **Body:** 1rem (16px), line-height 1.5
- **Numbers:** tabular-nums, slightly larger weight. Weights and quantities are the most important data

## Spacing
- Base unit: 0.5rem (8px)
- Section gap: 1.5rem
- Card padding: 1.25rem
- Compact mode for tables: 0.5rem cell padding

## Elevation
- Cards: subtle border + very light shadow (0 1px 3px oklch(0% 0 0 / 0.08))
- Dropdowns/modals: stronger shadow (0 4px 12px oklch(0% 0 0 / 0.15))
- No floating elements unless necessary

## Component Patterns
- **Status badges:** Pill-shaped, colored background with matching text. Not just colored dots
- **Data tables:** Alternating row backgrounds, sticky headers, right-align numbers
- **Number displays:** Mono font, larger size, right-aligned in tables
- **Action buttons:** Primary (filled), Secondary (outlined), Danger (red filled)
- **Navigation:** Top navbar with logo, collapsible sidebar not needed (pages are separate HTML files)
- **Forms:** Labels above inputs, generous touch targets, clear required indicators
- **Empty states:** Helpful message + action button, not just blank space

## Layout
- Max content width: 1400px for dashboard, full-width for tables
- Sidebar: none (separate pages model)
- Responsive: tables scroll horizontally on mobile, cards stack vertically
