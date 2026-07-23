# Browser validation results

Date: 2026-07-22 (Asia/Shanghai)

Target: optimized Next.js production build at `http://localhost:3000`, connected to the local FastAPI evaluator stack.

## Route sweep

All 18 fixed product routes rendered a non-empty page with no `Application Error`, `Runtime error`, `Hydration failed`, or `Internal Server Error` text:

- `/`
- `/app/consent`
- `/app/devices`
- `/app/devices/bind`
- `/app/memory`
- `/app/memory/mem_001`
- `/app/memory/delete`
- `/app/migrate`
- `/app/migrate/complete` (correctly redirected to `/app/migrate` when the clean seed had no completed migration)
- `/console`
- `/console/apps`
- `/console/apps/app_luna`
- `/console/apps/new`
- `/console/devices`
- `/console/memory/policy`
- `/console/memory/users`
- `/console/quickstart`
- `/console/settings`

The dynamic `/invite/[token]` route was validated with a newly issued real invite token instead of a fixed route.

## Real browser actions

| Surface | Action | Observed result |
|---|---|---|
| Console apps | Create `Browser Matrix App` | Backend-created app returned a one-time `mp_sandbox_*` key and the UI required saving it before continuing. |
| Quickstart | Send test event, then retrieve | Both HTTP operations succeeded; the UI advanced only after the responses and displayed the real event and trace identifiers. |
| Policy | Toggle sensitive-memory retrieval on, then off | Server response drove both states; the original setting was restored. |
| Team | Issue Support invite | Pending invite and real `/invite/<token>` URL rendered. |
| Public invite | Preview and accept invite | Tenant/email/role previewed, acceptance persisted `Browser Matrix Member`, and the token became consumed. |
| Console memory | Edit active record | A new backend version ID replaced the edited source row immediately. |
| Console memory | Archive edited version | Row changed to `Archived` using the returned record. |
| Console memory | Delete archived record | Backend accepted the tombstone and the row immediately disappeared from the default list. |
| Consent | Explicitly set memory off, then on | Both requests completed without optimistic success; final state restored to on. |
| Memory Center | Add explicit memory | Real ingest completed and the new memory appeared in the list. |
| Memory Center | Export | A real JSON bundle downloaded; UI reported 40 active memories. |
| Device bind | Register test device and bind one-time code | Real device ID/code returned; bound device appeared on `/app/devices`. |
| Migration | Select all recommended and execute | 35 moved, 5 skipped, 0 failed; completion route rendered and old v1 access was removed as selected. |
| Memory detail | Report as wrong | Status changed to `flagged_wrong`; UI reported that recall was stopped pending review. |
| Memory detail | Delete flagged-wrong record | Tombstone succeeded and navigation returned to Memory Center. |
| Delete all | Type `DELETE` and confirm | One atomic delete-user request completed and Memory Center showed no memories. |

## Backend-offline behavior

With only `mp-backend` stopped:

- `/app/memory` rendered the demo dataset, showed the explicit backend-offline notice, and disabled both Pause and Tell Luna.
- `/console/memory/users` remained readable; Edit, Archive, and Delete were disabled inside the action menu.
- No success notification was shown and no demo record was mutated.

The backend was restarted, became healthy, and browser writes resumed.

## Defects found during this browser pass

The pass exposed three additional cross-layer defects, all fixed and retested in the same run:

1. A versioned edit returned a new memory ID, but the store tried to replace by that new ID and left the old row visible.
2. The UI offered Delete for archived records while the backend only allowed `active -> deleted`.
3. A successful tombstone remained visible locally even though the default backend list excludes deleted records.

Regression tests now cover all three cases. The final production-browser sequence edit -> archive -> delete passed.
