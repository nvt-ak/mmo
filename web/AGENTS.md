<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Tailwind v4 — CSS variables

Use parenthesis syntax for theme/CSS vars. **Do not** use arbitrary `[var(...)]`.

| Avoid | Prefer |
|-------|--------|
| `bg-[var(--surface-muted)]` | `bg-(--surface-muted)` |
| `text-[var(--muted)]` | `text-(--muted)` |
| `border-[var(--border)]` | `border-(--border)` |
| `hover:bg-[var(--surface-muted)]` | `hover:bg-(--surface-muted)` |
| `bg-(--surface-muted)/60` | opacity suffix OK on `(--var)` |

Tokens live in `src/app/globals.css` (`--canvas`, `--surface`, `--muted`, etc.).

**Enforced in Cursor:** `.cursor/rules/web-frontend.mdc` (auto when editing `web/**/*`).
