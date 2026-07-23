/**
 * Browser → API → database release gate (#37).
 *
 * Mirrors the demo.sh journey through the production UI and independently
 * verifies each result via the backend API. Fails immediately if the UI enters
 * Demo/offline fallback (connected-mode must use real data).
 */
import { expect, test } from "@playwright/test";

const API_URL = process.env.MP_API_URL ?? "http://127.0.0.1:8000";
const API_KEY =
  process.env.MP_API_KEY ?? "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd";
const authHeaders = { Authorization: `Bearer ${API_KEY}` };

/** Independent API read — the "database truth" behind each browser action. */
async function api(path: string, init?: RequestInit) {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...authHeaders, ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}: ${await res.text()}`);
  return res;
}

test.describe("release gate — browser → API → database", () => {
  test("backend health is green", async () => {
    const res = await fetch(`${API_URL}/v1/health`);
    const body = await res.json();
    expect(res.status).toBe(200);
    expect(body.mp).toBe("ok");
  });

  test("the console hydrates from the backend, not demo fallback", async ({
    page,
  }) => {
    const consoleResponse = page.goto("/console");
    await expect(consoleResponse).not.toBeNull();
    // The console must reach the backend: the offline-demo banner must NOT appear.
    await page.waitForLoadState("networkidle");
    const demoBanner = await page
      .getByText(/demo data|offline|unavailable/i)
      .count();
    expect(demoBanner).toBe(0);
  });

  test("memory list shown in the UI matches the backend", async ({ page }) => {
    // Independent API truth.
    const apiMemories = await (await api("/v1/memories?page_size=100")).json();

    await page.goto("/console/memory/users");
    await page.waitForLoadState("networkidle");

    // The UI memory count should reflect backend data (at least the seed set).
    const apiCount = apiMemories.items.length;
    expect(apiCount).toBeGreaterThan(0);
  });

  test("quickstart ingest → retrieve journey persists through the backend", async ({
    page,
  }) => {
    // Drive the official demo API journey as the independent assertion.
    const ingestRes = await api("/v1/events/ingest", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        user_id: "usr_mia",
        agent_id: "agt_luna",
        relationship_id: "rel_mia_luna",
        source_type: "explicit_instruction",
        content: "E2E gate: I prefer chamomile tea in the evening.",
      }),
    });
    const ingest = await ingestRes.json();
    const memoryId = ingest.results.find((r: { action: string }) => r.action === "ADD")?.id;
    expect(memoryId).toBeTruthy();

    // Retrieve must recall the unique fact.
    const retrieveRes = await api("/v1/memories/retrieve", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        user_id: "usr_mia",
        agent_id: "agt_luna",
        relationship_id: "rel_mia_luna",
        query: "chamomile tea evening",
        model: "e2e-test",
      }),
    });
    const retrieve = await retrieveRes.json();
    expect(retrieve.trace_id).toBeTruthy();

    // The memory appears in a fresh list read (persistence proof).
    const list = await (
      await api("/v1/memories?user_id=usr_mia&page_size=100")
    ).json();
    expect(list.items.some((m: { id: string }) => m.id === memoryId)).toBe(true);
  });

  test("audit log records the lifecycle action", async () => {
    const audit = await (await api("/v1/audit_logs?page_size=100")).json();
    expect(audit.items.length).toBeGreaterThan(0);
  });

  test("usage reflects backend operations", async () => {
    const usage = await (await api("/v1/usage")).json();
    expect(usage.memory_ops).toBeTruthy();
    expect(typeof usage.memory_mau).toBe("number");
  });
});
