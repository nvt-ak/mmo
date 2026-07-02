# US-003 Design Document

## Architecture

```text
Browser
  ↓
Next.js App Router (web/src/app/*)
  ↓
Feature components (client components)
  ↓
TanStack React Query (cache + mutations)
  ↓
api client (web/src/lib/api/client.ts)
  ↓ fetch JSON
US-002 FastAPI (localhost:8000)
```

## App Structure

```text
web/src/
  app/
    layout.tsx          # Root layout + AppShell + Providers
    page.tsx            # redirect → /today
    today/page.tsx      # Inbox
    sources/page.tsx    # Channels
    settings/page.tsx   # Weights & niche
    insights/page.tsx   # Learning
  components/
    layout/app-shell.tsx
    inbox/              # inbox-page, reject-modal, report-dialog
    sources/sources-page.tsx
    settings/settings-page.tsx
    insights/insights-page.tsx
    shared/score-badge.tsx
  lib/
    api/client.ts       # fetch wrapper + api object
    api/types.ts        # TypeScript contracts
    providers.tsx       # QueryClientProvider
```

## Layout & Navigation

`AppShell` — fixed sidebar (56 width), 4 nav links, active state via `usePathname()`.

| Route | Component | Primary API calls |
| --- | --- | --- |
| `/today` | `InboxPage` | `listSuggestions`, `bulkApprove`, `bulkReject`, `reportSuggestion`, `improveSuggestion` |
| `/sources` | `SourcesPage` | `listChannels`, `addChannel`, `updateChannelScan`, `deleteChannel`, `runScan` |
| `/settings` | `SettingsPage` | `getSettings`, `updateSettings` |
| `/insights` | `InsightsPage` | `getInsights`, `runLearningCycle` |

## Inbox UX

- **Tabs:** pending | approved | reported | rejected
- **Search:** debounced via query key (`search` param)
- **Selection:** checkbox per row + select all
- **Actions:** bulk approve, bulk reject (modal with reason), per-row report (dialog), improve
- **Polling:** `refetchInterval: 30_000` on suggestion list
- **Score display:** `ScoreBadge` from `final_score` + component breakdown tooltip

### Reject Reasons

Matches backend enum: `too_broad`, `too_competitive`, `off_topic`, `poor_quality`, `other`.

## State Management

| Pattern | Usage |
| --- | --- |
| React Query `useQuery` | Read endpoints (suggestions, channels, settings, insights) |
| React Query `useMutation` | Write endpoints; `invalidateQueries` on success |
| Local `useState` | UI-only: selection set, modals, form drafts |

Query keys:

- `["suggestions", status, search]`
- `["channels"]`
- `["settings"]`
- `["insights"]`

## API Client

- Base URL: `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`
- Errors: `ApiError` with status + message from backend `{ error: { message } }`
- All paths prefixed `/api/v1/` except `/health`

Types in `types.ts` mirror backend Pydantic schemas (`Suggestion`, `Channel`, `SettingsResponse`, etc.).

## Settings Form Pattern

`SettingsForm` child component initializes state from props (no `useEffect` sync).
Parent remounts form via `key` when server data changes after save/refetch.

## Styling

- Tailwind CSS v4
- CSS variables in `globals.css`: `--surface`, `--sidebar`, `--accent-muted`, `--border`
- Light content panels on white; dark sidebar

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |

Copy from `web/.env.local.example`.

## Error Handling

- Query errors: inline red text `(error as Error).message`
- Mutation errors: toast-like message banner (sources page) or modal stays open (reject)
- No global error boundary (future improvement)

## Dependencies on US-002

Frontend assumes backend running with CORS allowing `localhost:3000`.
Breaking API shape changes require coordinated updates to `types.ts` + `client.ts`.
