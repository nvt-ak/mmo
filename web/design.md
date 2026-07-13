# Design — VideoScout Web

A locked design system for the VideoScout operator UI. Every page reads this file
before emitting styles. Extend or amend here when the system grows — do not
override per page.

## Genre

editorial — warm bone operator desk, document-style density, hairline structure.

## Macrostructure family

- **Inbox / list pages** (`/today`, `/batch`, `/feedback`, `/sources`, `/pool`): Workbench — compact header, sticky action bar, rule-separated data tables.
- **Form / settings** (`/settings`, modals): Workbench panels — stacked sections with hairline borders, no card hover lift.
- **Insights / profiles**: Workbench + stat strip in page header.

## Theme

- `--color-paper`   oklch(97.2% 0.006 85)
- `--color-paper-2` oklch(99.5% 0.002 85)
- `--color-paper-3` oklch(98% 0.004 85)
- `--color-ink`     oklch(34% 0.012 265)
- `--color-ink-2`   oklch(14% 0 0)
- `--color-rule`    oklch(92.5% 0.004 265)
- `--color-accent`  oklch(14% 0 0)
- `--color-focus`   oklch(45% 0.12 250)

## Typography

- Display: Newsreader 500, style normal — page titles only.
- Body: Geist Sans 400 — UI, tables, forms.
- Mono: Geist Mono 400 — metadata, counts, API status.
- Display tracking: -0.02em on `.font-editorial`.

## Spacing

4-point named scale in `tokens.css`. Use `var(--space-*)` in CSS; Tailwind spacing in TSX where already established.

## Motion

- Easings: `--ease-out`, `--ease-in`, `--ease-in-out`.
- Reveal: none on data tables; optional 150ms opacity on empty states only.
- Reduced-motion: opacity-only, ≤ 150ms.

## Microinteractions stance

- Silent success — inline status text, no toasts.
- Hover tooltips: 800ms delay if added later; focus: 0ms.
- Buttons: 8 states (default · hover · focus · active · disabled · loading · error · success).

## CTA voice

- Primary: ink fill (`--color-accent`), 4px radius, sentence-case verbs.
- Secondary: paper fill + hairline rule border.
- Ghost: transparent, muted text, paper-3 hover.

## Per-page allowances

- App pages: no hero enrichment, no ambient gradients, no staggered table rows.
- Modals: flat `surface-card`, no entrance animation.

## What pages MUST share

- Side-rail navigation with left accent bar on active route.
- Newsreader page titles + Geist body.
- Ink primary buttons and pastel semantic tags.
- Hairline borders (`--color-rule`), not heavy shadows.

## What pages MAY differ on

- Stat strip density in header meta.
- Table vs panel layout within Workbench family.
- Grid column count on insights (2-col vs full-width table).

## Exports

### tokens.css

See `web/tokens.css` — source of truth.

### Tailwind v4 `@theme`

```css
@theme inline {
  --color-background: var(--color-paper);
  --color-foreground: var(--color-ink);
  --font-sans: var(--font-body);
  --font-serif: var(--font-display);
  --font-mono: var(--font-outlier);
}
```

### DTCG `tokens.json`

```json
{
  "color": {
    "paper": { "$value": "oklch(97.2% 0.006 85)", "$type": "color" },
    "ink": { "$value": "oklch(34% 0.012 265)", "$type": "color" },
    "accent": { "$value": "oklch(14% 0 0)", "$type": "color" }
  },
  "font": {
    "display": { "$value": "Newsreader", "$type": "fontFamily" },
    "body": { "$value": "Geist Sans", "$type": "fontFamily" }
  }
}
```

### shadcn/ui CSS variables

```css
:root {
  --background: 97.2% 0.006 85;
  --foreground: 34% 0.012 265;
  --primary: 14% 0 0;
  --primary-foreground: 100% 0 0;
  --muted: 92.5% 0.004 265;
  --muted-foreground: 52% 0.008 265;
  --border: 92.5% 0.004 265;
  --ring: 45% 0.12 250;
  --radius: 6px;
}
```
