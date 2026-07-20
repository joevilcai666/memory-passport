# CLAUDE.md

@AGENTS.md

This file guides AI agents (Claude Code, etc.) working in the Memory Passport repo. Read it before touching anything.

---

## What this is

**Memory Passport** — a 100%-interactive **prototype** of a B2B2C portable memory infrastructure for AI companions and robots. The one-liner: **"换设备，不换关系；换模型，不换记忆"** (switch devices, not relationships; switch models, not memory).

- It is a **prototype**: seeded mock data, no real backend, no real API keys, no Supabase. All state lives in a Zustand store.
- The canonical demo story is **Luna** — a hybrid (software + robot) companion app. Luna Robot v1→v2 migration is the **wedge** (the hero moment).
- Full PRD lives at `docs/prds/Memory Passport PRD v2.0.md` — read it for strategy/data model/API. The PRD has been aligned to this prototype (Appendix C records the diff vs the original draft).

---

## Tech stack (do not reinvent)

- **Next.js 16** (App Router, Turbopack) + **React 19** + **TypeScript** (`src/` dir, `@/*` alias)
- **Tailwind CSS v4** — tokens via `@theme inline` in `src/app/globals.css` (NOT a `tailwind.config`). Read `globals.css` before adding color/radius utilities.
- **shadcn/ui** (new-york style) on **Radix** — components in `src/components/ui/*`. Add new ones by writing the file there, matching the `data-slot` convention; do NOT run the interactive `shadcn` CLI.
- **`geist`** package → `GeistSans` / `GeistMono` via `next/font` in `src/app/layout.tsx`. All numbers/IDs/model names use the `.tabular` class (mono + tabular-nums).
- **framer-motion** for animation (minimal & functional — only the migration-complete page has an "earned" signature animation).
- **Recharts** for the Overview activity chart.
- **lucide-react** for icons (default 16px, `strokeWidth={1.5}`).
- **Zustand** store at `src/store/memory-store.ts` — single store, seeded from `src/lib/mock-data.ts`. **All mutations are live** (toggle policy, edit/delete memory, run migration, delete-all) and update the UI immediately.
- **sonner** toasts — there is one global `<Toaster />` in the root layout. Use `import { toast } from "sonner"`. Do NOT mount a local `<Toaster />` per page.
- **next-themes** for dark/light. Console defaults to dark; C-side forces light via `.paper-surface`.

Package manager is **pnpm**. Node 22+.

---

## Design system: "Ink & Paper"

Adapted from the Anyway Design System's *discipline* (neutral chrome, borders-over-shadows, Geist, radius hierarchy, token architecture) — **not** its tokens or gold brand color.

- **Accent:** passport-ink indigo `#1E3A8A`, exposed as `--primary` / `bg-primary` / `text-primary` / `text-ink-*`. Hue is reserved for status/data + the ink accent; chrome is monochrome neutral.
- **Two surfaces:**
  - **B-side Console** (`/console/*`) — graphite instrument-panel, defaults dark.
  - **C-side Embedded** (`/app/*`) — warm **paper** (`#FAF8F3`), forced light via the `.paper-surface` class on `AppShell`. The `.paper-surface` class redefines the CSS vars so it overrides `.dark` on `<html>`.
- **Radius:** 8 (buttons) / 10 (inputs) / 14 (cards) / full (pills, badges).
- **Elevation:** borders over shadows. Cards use `shadow-sm` only.
- **Type:** page titles `text-2xl font-medium tracking-tight`; marketing/hero 600 with negative tracking. See `globals.css` for the full token list.

Before designing anything new, skim `src/app/globals.css` (tokens) and a couple of existing pages (e.g. `src/app/console/memory/users/page.tsx`, `src/app/app/migrate/page.tsx`) to match the idiom.

---

## Architecture map

### Routes

Two App Router groups + a landing page. **Every route is real and clickable — no dead links.**

```
/                          Landing — the wedge + Privy analogy + 4-axis table
/console/*                 B-side Admin Console (ConsoleShell: sidebar + topbar + page)
  /console                 Overview (KPIs, activity chart, alerts, onboarding banner, migration demo)
  /console/apps            App list
  /console/apps/new        Create app (live consent preview)
  /console/apps/[id]       App detail + API keys
  /console/quickstart      "Get started" — 4-step SDK integration + live checklist
  /console/memory/policy   Auto-write rules + 4-axis portability toggles + retrieval
  /console/memory/users    Users (merged Debugger + End Users) — master-detail, click row → Trace Sheet
  /console/devices         Devices (migration-first: health tiles, upgrade path, registry)
  /console/settings        Team + Audit log
/app/*                     C-side Embedded UI (AppShell: phone-width, paper surface, Powered-by watermark)
  /app/consent             Memory consent
  /app/memory              Memory Center
  /app/memory/[id]         Memory detail (portability badges, source, used-by)
  /app/memory/delete       Delete all (type DELETE)
  /app/devices             Device management
  /app/devices/bind        Robot binding (QR scan + pairing code)
  /app/migrate             Migration Preview — THE HERO (3 buckets)
  /app/migrate/complete    Migration Complete — stamp animation, v2 inherits
```

### Key components

- `src/components/shell/` — `ConsoleShell`, `Sidebar`, `Topbar` (has the "Preview as user" dropdown), `PageHeader`, `AppShell`.
- `src/components/brand/` — `StampMark` (the passport-stamp logo), `PoweredByMemoryPassport` (the watermark — **must appear on every C-side screen**).
- `src/components/memory/` — `MemoryCard`, `PortabilityBadges` (full + compact modes), `MemoryTraceSheet` (right-side drawer; reused on the Users page), `InChatConfirmationCard`.
- `src/components/console/` — `KpiTile`, `ActivityChart`.
- `src/components/ui/` — shadcn primitives. Treat as generated; match their patterns.

### Data

- `src/lib/types.ts` — every domain entity (User, Agent, Device, Relationship, MemoryRecord with portability + model_provenance, Migration, etc.). **The source of truth for shapes.**
- `src/lib/mock-data.ts` — the Luna dataset (42 memories across Preferences/Relationship/Events/Boundaries/Tasks/Archived, v1+v2 devices, one in-progress migration, audit logs, KPIs). Copy in the PRD comes straight from here.
- `src/store/memory-store.ts` — Zustand store + all mutations. Read selectors narrowly (e.g. `useMemoryStore(s => s.memories)`) to avoid re-render storms.

---

## Conventions & gotchas

- **Never `<button>` inside `<button>`.** Invalid HTML → React hydration error. If you need a clickable container that holds other buttons, use `<div role="button" tabIndex={0}>` with an `onKeyDown` handler (see the `Bucket` component in `src/app/app/migrate/page.tsx`).
- **Navigation links use `next/link`'s `<Link>`**, never raw `<a>` for internal routes (the `@next/next/no-html-link-for-pages` lint rule is enforced).
- **Hydration-safe theme toggle:** the `useMounted()` helper in `Topbar.tsx` uses `useSyncExternalStore` (not setState-in-effect, which trips `react-hooks/set-state-in-effect`).
- **Portability must be visible.** Memory Detail shows the 4 axes as ✓/✕ badges; the compact badge says "Portable · 3/4" or "Device-local". This is the productized "memory travels with me" — don't hide it.
- **Trace must label the model.** `Model: gpt-4o` is explicit in the Trace Sheet; cross-model parity is rendered from `memory.model_provenance.retrieval_history`. This is the cross-model moat made observable.
- **"Powered by Memory Passport"** appears on every C-side screen footer (consent, Memory Center, migration complete) and on the landing page. Non-negotiable — it's the network-effect seed.
- **Migration is honest.** The 3 buckets (Recommended / Needs review / Not moved) tell the user the truth about what can't travel (device-local sensor data, etc.). Don't make migration look like a full copy.
- **`cross_brand_app` portability axis is locked OFF** in V0.1 (P2/P3). The Policy toggle renders it disabled with a "P2 · deferred" note. Don't enable it.
- IDs, serials, counts, model names, timestamps-as-data → `.tabular` (mono + tabular-nums). Prose stays in Geist Sans.

---

## Commands

```bash
pnpm dev      # dev server on :3000 (Turbopack)
pnpm build    # production build — must pass with 0 errors before commit
pnpm lint     # eslint — must pass clean (0 errors, 0 warnings is the bar)
```

The dev server auto-restarts. There is no test runner (prototype).

---

## Workflow

1. **Read before writing.** Match the surrounding code's comment density, naming, and idiom. This codebase reads like a precise instrument panel on the B-side and warm paper on the C-side — preserve that split.
2. **Keep the build green.** Run `pnpm lint && pnpm build` before considering work done. TypeScript errors and lint warnings are not acceptable.
3. **Mock data is the contract.** If you need a new entity/field, add it to `src/lib/types.ts` and seed it in `src/lib/mock-data.ts` — then the store and UI follow.
4. **Don't add a backend.** This is a prototype. No API routes, no Supabase, no real fetches. State lives in Zustand.
5. **Commit messages** follow the existing style: a short imperative subject + optional body with bullet points (see `git log`).

---

## The wedge (keep this front of mind)

The entire product hinges on **one demo moment**: a user upgrades Luna Robot v1 → v2 and the relationship memory follows. Migration Preview (`/app/migrate`) → Complete (`/app/migrate/complete`, with the stamp animation + "I still remember you call me Luna") is the hero. Everything else exists to make that moment credible and reachable. When in doubt about priorities, optimize the migration flow.
