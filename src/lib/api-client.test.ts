import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/lib/api-client";

type LooseClient = typeof api & Record<string, (...args: never[]) => Promise<unknown>>;

const client = api as LooseClient;

function fetchMock() {
  return vi.mocked(globalThis.fetch);
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function expectRequest(
  index: number,
  path: string,
  method = "GET",
  body?: unknown,
) {
  const [url, init] = fetchMock().mock.calls[index];
  expect(url).toBe(`http://127.0.0.1:8000${path}`);
  expect(init?.method ?? "GET").toBe(method);
  expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer mp_test_key");
  if (body !== undefined) {
    expect(JSON.parse(String(init?.body))).toEqual(body);
  }
}

beforeEach(() => {
  client.configureCredential?.("mp_test_key", "key_current");
});

describe("API surface", () => {
  it.each([
    "configureCredential",
    "getApps",
    "getApp",
    "createApp",
    "createApiKey",
    "rotateApiKey",
    "getPolicy",
    "setUserConsent",
    "createExport",
    "getExportStatus",
    "downloadExport",
    "deleteUser",
    "registerDevice",
    "bindDevice",
    "unbindDevice",
    "wipeDevice",
    "getTeam",
    "inviteTeamMember",
    "previewTeamInvite",
    "acceptTeamInvite",
    "getTrace",
    "recordTraceFeedback",
    "ingestEvent",
    "retrieveMemories",
    "patchMemory",
    "deleteMemory",
    "getMigration",
    "previewMigration",
    "executeMigration",
    "rollbackMigration",
  ])("exposes %s", (method) => {
    expect(typeof client[method]).toBe("function");
  });
});

describe("apps, keys, and runtime credentials", () => {
  it("maps list/detail/create/key calls to the backend contracts", async () => {
    const app = { id: "app_1", name: "Luna", api_keys: [] };
    const secret = { id: "key_1", key: "mp_live_secret" };
    fetchMock()
      .mockResolvedValueOnce(jsonResponse({ items: [app] }))
      .mockResolvedValueOnce(jsonResponse(app))
      .mockResolvedValueOnce(jsonResponse({ app, api_key: secret }, 201))
      .mockResolvedValueOnce(jsonResponse(secret, 201))
      .mockResolvedValueOnce(jsonResponse({ ...secret, id: "key_2" }, 201));

    await client.getApps();
    await client.getApp("app_1");
    await client.createApp({
      name: "Luna",
      product_type: "software",
      environment: "sandbox",
      data_region: "us-east-1",
      show_powered_by: true,
    });
    await client.createApiKey("app_1", {
      label: "Production",
      environment: "production",
    });
    await client.rotateApiKey("app_1", "key_other");

    expectRequest(0, "/v1/apps");
    expectRequest(1, "/v1/apps/app_1");
    expectRequest(2, "/v1/apps", "POST", {
      name: "Luna",
      product_type: "software",
      environment: "sandbox",
      data_region: "us-east-1",
      show_powered_by: true,
    });
    expectRequest(3, "/v1/apps/app_1/api-keys", "POST", {
      label: "Production",
      environment: "production",
    });
    expectRequest(4, "/v1/apps/app_1/api-keys/key_other/rotate", "POST");
  });

  it("uses the replacement secret after rotating the active credential", async () => {
    client.configureCredential("mp_old", "key_current");
    fetchMock()
      .mockResolvedValueOnce(
        jsonResponse({ id: "key_replacement", key: "mp_new" }, 201),
      )
      .mockResolvedValueOnce(jsonResponse({ items: [] }));

    await client.rotateApiKey("app_1", "key_current");
    await client.getApps();

    const firstHeaders = new Headers(fetchMock().mock.calls[0][1]?.headers);
    const secondHeaders = new Headers(fetchMock().mock.calls[1][1]?.headers);
    expect(firstHeaders.get("Authorization")).toBe("Bearer mp_old");
    expect(secondHeaders.get("Authorization")).toBe("Bearer mp_new");
  });
});

describe("policy, consent, export, and delete-user contracts", () => {
  it("uses authenticated response bodies, including Blob downloads", async () => {
    fetchMock()
      .mockResolvedValueOnce(jsonResponse({ id: "pol_1" }))
      .mockResolvedValueOnce(jsonResponse({ id: "usr_1", memory_enabled: false }))
      .mockResolvedValueOnce(jsonResponse({ export_id: "exp_1" }, 202))
      .mockResolvedValueOnce(
        jsonResponse({
          export_id: "exp_1",
          status: "completed",
          download_url: "/v1/exports/exp_1/download?token=once",
        }),
      )
      .mockResolvedValueOnce(
        new Response('{"memories":[]}', {
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ user_id: "usr_1", tombstoned_memories: 3 }),
      );

    await client.getPolicy("app_1", "agt_1");
    await client.setUserConsent("usr_1", false);
    await client.createExport("usr_1");
    const status = await client.getExportStatus("exp_1");
    const blob = await client.downloadExport(status.download_url);
    await client.deleteUser("usr_1");

    expect(blob).toBeInstanceOf(Blob);
    expectRequest(0, "/v1/policies?app_id=app_1&agent_id=agt_1");
    expectRequest(1, "/v1/users/usr_1/consent", "PATCH", {
      memory_enabled: false,
    });
    expectRequest(2, "/v1/exports", "POST", { user_id: "usr_1", format: "json" });
    expectRequest(3, "/v1/exports/exp_1");
    expectRequest(4, "/v1/exports/exp_1/download?token=once");
    expectRequest(5, "/v1/delete_user", "POST", { user_id: "usr_1" });
  });
});

describe("device, team, and feedback contracts", () => {
  it("covers every device state transition", async () => {
    fetchMock()
      .mockResolvedValueOnce(jsonResponse({ device: { id: "dev_1" }, pairing_code: "123" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "dev_1", status: "bound" }))
      .mockResolvedValueOnce(jsonResponse({ id: "dev_1", status: "unbound" }))
      .mockResolvedValueOnce(jsonResponse({ device: { id: "dev_1" }, tombstoned_memories: 2 }));

    await client.registerDevice({
      model: "Luna Home",
      generation: "v2",
      serial_number_hash: "sha256",
    });
    await client.bindDevice({ device_id: "dev_1", user_id: "usr_1", pairing_code: "123" });
    await client.unbindDevice("dev_1");
    await client.wipeDevice("dev_1");

    expectRequest(0, "/v1/devices/register", "POST", {
      model: "Luna Home",
      generation: "v2",
      serial_number_hash: "sha256",
    });
    expectRequest(1, "/v1/devices/bind", "POST", {
      device_id: "dev_1",
      user_id: "usr_1",
      pairing_code: "123",
    });
    expectRequest(2, "/v1/devices/unbind", "POST", { device_id: "dev_1" });
    expectRequest(3, "/v1/devices/wipe", "POST", { device_id: "dev_1" });
  });

  it("covers team listing/invites and persisted trace feedback", async () => {
    fetchMock()
      .mockResolvedValueOnce(jsonResponse({ members: [], pending_invites: [] }))
      .mockResolvedValueOnce(jsonResponse({ invite: { id: "tmi_1" }, token: "invite-token" }, 201))
      .mockResolvedValueOnce(jsonResponse({ email: "new@example.com", role: "Support" }))
      .mockResolvedValueOnce(jsonResponse({ id: "tm_1", email: "new@example.com" }))
      .mockResolvedValueOnce(jsonResponse({ id: "trc_1", feedback: null }))
      .mockResolvedValueOnce(
        jsonResponse({
          id: "trc_1",
          feedback: { memory_id: "mem_1", category: "useful" },
        }),
      );

    await client.getTeam();
    await client.inviteTeamMember({ email: "new@example.com", role: "Support" });
    await client.previewTeamInvite("invite-token");
    await client.acceptTeamInvite("invite-token", { name: "New Person" });
    await client.getTrace("trc_1");
    await client.recordTraceFeedback("trc_1", {
      memory_id: "mem_1",
      category: "useful",
    });

    expectRequest(0, "/v1/team");
    expectRequest(1, "/v1/team/invites", "POST", {
      email: "new@example.com",
      role: "Support",
    });
    expectRequest(2, "/v1/public/team-invites/invite-token");
    expectRequest(3, "/v1/public/team-invites/invite-token/accept", "POST", {
      name: "New Person",
    });
    expectRequest(4, "/v1/debug/traces/trc_1");
    expectRequest(5, "/v1/debug/traces/trc_1/feedback", "POST", {
      memory_id: "mem_1",
      category: "useful",
    });
  });
});

describe("memory and migration contracts", () => {
  it("covers ingest, retrieve, CRUD, preview, execute, read, and rollback", async () => {
    fetchMock()
      .mockResolvedValueOnce(jsonResponse({ event_id: "evt_1", results: [] }, 201))
      .mockResolvedValueOnce(jsonResponse({ trace_id: "trc_1", results: [] }))
      .mockResolvedValueOnce(jsonResponse({ id: "mem_1", content: "updated" }))
      .mockResolvedValueOnce(jsonResponse({ id: "mem_1", status: "deleted" }))
      .mockResolvedValueOnce(
        jsonResponse({
          migration_id: "mig_1",
          recommended: { memory_ids: ["mem_1"] },
          needs_review: { memory_ids: ["mem_2"] },
          not_moved: { memory_ids: ["mem_3"] },
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ id: "mig_1", status: "completed" }))
      .mockResolvedValueOnce(jsonResponse({ id: "mig_1", status: "completed" }))
      .mockResolvedValueOnce(jsonResponse({ id: "mig_1", status: "rolled_back" }));

    await client.ingestEvent({
      user_id: "usr_1",
      agent_id: "agt_1",
      relationship_id: "rel_1",
      source_type: "chat",
      content: "Remember tea",
    });
    await client.retrieveMemories({
      user_id: "usr_1",
      agent_id: "agt_1",
      relationship_id: "rel_1",
      query: "tea",
    });
    await client.patchMemory("mem_1", { content: "updated" });
    await client.deleteMemory("mem_1");
    await client.previewMigration({
      user_id: "usr_1",
      source_relationship_id: "rel_old",
      target_relationship_id: "rel_new",
      source_device_id: "dev_old",
      target_device_id: "dev_new",
    });
    await client.executeMigration({
      migration_id: "mig_1",
      selected_memory_ids: ["mem_1"],
      old_device_access: "remove",
    });
    await client.getMigration("mig_1");
    await client.rollbackMigration("mig_1");

    expectRequest(0, "/v1/events/ingest", "POST");
    expectRequest(1, "/v1/memories/retrieve", "POST");
    expectRequest(2, "/v1/memories/mem_1", "PATCH", { content: "updated" });
    expectRequest(3, "/v1/memories/mem_1", "DELETE");
    expectRequest(4, "/v1/migrations/preview", "POST");
    expectRequest(5, "/v1/migrations/execute", "POST");
    expectRequest(6, "/v1/migrations/mig_1");
    expectRequest(7, "/v1/migrations/mig_1/rollback", "POST");
  });
});

describe("structured errors", () => {
  it("parses backend status, code, message, and detail", async () => {
    fetchMock().mockResolvedValueOnce(
      jsonResponse(
        {
          detail: {
            code: "memory_disabled",
            message: "memory is disabled",
            user_id: "usr_1",
          },
        },
        409,
      ),
    );

    const error = await client
      .ingestEvent({
        user_id: "usr_1",
        agent_id: "agt_1",
        relationship_id: "rel_1",
        source_type: "chat",
        content: "No",
      })
      .catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      code: "memory_disabled",
      message: "memory is disabled",
      detail: {
        code: "memory_disabled",
        message: "memory is disabled",
        user_id: "usr_1",
      },
    });
  });
});
