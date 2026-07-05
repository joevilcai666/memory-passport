# Memory Passport — Interactive Prototype

> **Switch devices, not relationships. Switch models, not memory.**

A 100%-interactive prototype of **Memory Passport** — a user-owned, cross-model, cross-device, portable long-term memory infrastructure for AI companions and robots. Built from PRD v2.0.

This is a **prototype**: seeded with the canonical **Luna** dataset (Luna companion app + Luna Robot v1→v2), purely client-side mock state, no backend.

---

## Quick start

```bash
pnpm install
pnpm dev
# open http://localhost:3000
```

Requires Node 22+ and pnpm 10+.

---

## The design language: "Ink & Paper"

A passport: memories are **ink stamps** — owned by you, traveling with you.

| Surface | Treatment |
|---|---|
| **B-side Console** (`/console/*`) | Graphite instrument-panel. Dense, data-heavy, credible. Defaults to dark. |
| **C-side Embedded** (`/app/*`) | Warm **paper**. Trust-centric, simple, consumer-facing. Forces light. |

- **Accent:** passport-ink indigo `#1E3A8A` (ownable — not the Anyway gold)
- **Typography:** Geist + Geist Mono (mono + tabular figures for all IDs, counts, model names)
- **Discipline:** neutral chrome, hue reserved for status/data; borders over shadows; radius hierarchy (8/10/14)
- **Adapted from** the Anyway Design System's *discipline* (token architecture, type scale, radius/shadow system), not its tokens or brand color.

---

## Walk the demo (the connected Luna story)

The prototype tells one end-to-end narrative. Follow this path:

1. **`/`** — The wedge. Two doorways: build (console) or experience (as a user).
2. **`/console/apps/new`** — Create the "Luna" app (hybrid: software + robot). Live consent preview.
3. **`/console/quickstart`** — Copy the sandbox key, click **Run test event** → a memory forms, then **Run retrieve test**. Checklist animates ✓.
4. **`/console/memory/policy`** — The 4 portability axes. Toggle them live. `cross_model` is the moat.
5. **`/app/consent`** — Turn memory on (Powered by watermark present).
6. **`/app/memory`** — 42 memories across categories. Tap one.
7. **`/app/memory/[id]`** — Source ("why saved?"), **portability badges** (✓✓✓), used-by list, edit/delete/report.
8. **`/console/memory/debugger`** → pick a memory → **trace** — see **Model: gpt-4o**, the projection, feedback, and **cross-model parity** (gpt-4o + claude-3.5).
9. **`/app/devices/bind`** — Scan Luna Robot v1's QR (simulated).
10. **`/app/migrate`** ← **THE HERO.** v1→v2. Three buckets: Recommended / Needs review / Not moved. Select, choose v1 access, **Move**.
11. **`/app/migrate/complete`** — Stamp animation. v2 inherits: *"I still remember you call me Luna…"*
12. **`/console/devices`** — The migration appears in Recent Migrations.

---

## Routes

### `/console/*` — B-side Admin Console
| Route | Description |
|---|---|
| `/console` | Overview: KPIs (MAU, Ops, Useful/False rate, Cross-Model Parity), activity chart, alerts |
| `/console/apps` | App list |
| `/console/apps/new` | Create app (name, type, env, region, branding) + live preview |
| `/console/apps/[id]` | App detail + API keys (reveal/copy/roll) |
| `/console/quickstart` | 4-step SDK integration + live status checklist |
| `/console/memory/policy` | Auto-write rules table + **4-axis portability toggles** + retrieval |
| `/console/memory/debugger` | Search user → memory records table, filters, actions |
| `/console/memory/debugger/[memoryId]/trace` | Request info (Model labeled), retrieved memories, projection, feedback, cross-model parity |
| `/console/memory/users` | End users list |
| `/console/devices` | Device models + Recent migrations |
| `/console/settings` | Team members (Owner/Admin/Support) + Audit log |

### `/app/*` — Embedded User UI (inside "Luna")
| Route | Description |
|---|---|
| `/app/consent` | Memory consent ("Luna can remember you") |
| `/app/memory` | Memory Center (ON/Pause, count, category chips, list) |
| `/app/memory/[id]` | Memory detail (source, portability, used-by, edit/delete/report) |
| `/app/memory/delete` | Delete all (type DELETE to confirm) |
| `/app/devices` | Device management |
| `/app/devices/bind` | Robot binding (QR scan + pairing code) |
| `/app/migrate` | **Migration Preview** — 3 buckets, the wedge |
| `/app/migrate/complete` | Migration complete — stamp animation, v2 inherits |

---

## Tech stack

| Concern | Library |
|---|---|
| Framework | Next.js 16 (App Router, Turbopack) + React 19 |
| Styling | Tailwind CSS v4 (`@theme` tokens) |
| Components | shadcn/ui (new-york) on Radix |
| Fonts | `geist` (Geist Sans + Geist Mono via `next/font`) |
| Icons | lucide-react |
| Charts | Recharts |
| Animation | framer-motion |
| State | Zustand (seeded mock — no backend) |

All state is live and mutable: toggle policy, edit/delete memories, run the migration, delete all — the store updates and the UI reflects it.

---

## Design principles honored (from the PRD)

- **"Powered by Memory Passport"** appears on every user-facing screen — the network-effect seed.
- **Portability is visible** — users *see* Portable (✓✓✓) vs Device-local on Memory Detail.
- **Trace labels the model** — `Model: gpt-4o` is explicit; cross-model parity is shown.
- **Migration is honest** — the 3 buckets (Recommended / Needs review / Not moved) tell the truth about what can't travel.
- **Memory belongs to the user** — viewable, editable, deletable, exportable, tombstone-proven.

---

*Prototype only. No real backend, no real users, no real API keys. The "Luna" persona is illustrative.*
