import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMock = vi.hoisted(() => ({
  ping: vi.fn(),
  getMemories: vi.fn(),
  getAuditLogs: vi.fn(),
  getUsage: vi.fn(),
  getApps: vi.fn(),
  getPolicy: vi.fn(),
  getMigration: vi.fn(),
  getTeam: vi.fn(),
  setUserConsent: vi.fn(),
  upsertPolicy: vi.fn(),
  patchMemory: vi.fn(),
  deleteMemory: vi.fn(),
  ingestEvent: vi.fn(),
  retrieveMemories: vi.fn(),
  getTrace: vi.fn(),
  createUser: vi.fn(),
  previewMigration: vi.fn(),
  executeMigration: vi.fn(),
  deleteUser: vi.fn(),
  createApp: vi.fn(),
  createApiKey: vi.fn(),
  rotateApiKey: vi.fn(),
  inviteTeamMember: vi.fn(),
  recordTraceFeedback: vi.fn(),
  registerDevice: vi.fn(),
  bindDevice: vi.fn(),
  unbindDevice: vi.fn(),
  wipeDevice: vi.fn(),
  createExport: vi.fn(),
  getExportStatus: vi.fn(),
  downloadExport: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
  api: apiMock,
  ApiError: class ApiError extends Error {},
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), warning: vi.fn(), success: vi.fn() },
}));

import { BackendUnavailableError, useMemoryStore } from "@/store/memory-store";

function resetStore() {
  useMemoryStore.setState(useMemoryStore.getInitialState(), true);
}

function activateLive() {
  useMemoryStore.setState({
    hydrated: true,
    backendReachable: true,
    dataMode: "live",
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  resetStore();
  apiMock.ping.mockResolvedValue(true);
  apiMock.getMemories.mockResolvedValue([]);
  apiMock.getAuditLogs.mockResolvedValue([]);
  apiMock.getUsage.mockResolvedValue({
    memory_mau: 0,
    ops: { ingest: 0, retrieve: 0, update: 0, delete: 0 },
    storage_bytes: 0,
    device_activations: 0,
    migration_count: 0,
  });
  apiMock.getApps.mockResolvedValue([]);
  apiMock.getPolicy.mockResolvedValue(null);
  apiMock.getMigration.mockResolvedValue(null);
  apiMock.getTeam.mockResolvedValue({ members: [], pending_invites: [] });
});

describe("hydration modes", () => {
  it("keeps demo data offline and marks the mode explicitly", async () => {
    const seeded = useMemoryStore.getState().memories;
    apiMock.ping.mockResolvedValue(false);

    await useMemoryStore.getState().hydrate();

    expect(useMemoryStore.getState()).toMatchObject({
      hydrated: true,
      backendReachable: false,
      dataMode: "offline-demo",
    });
    expect(useMemoryStore.getState().memories).toEqual(seeded);
    expect(apiMock.getMemories).not.toHaveBeenCalled();
  });

  it("treats an empty live memory list as authoritative and hydrates optional resources", async () => {
    const liveApp = {
      ...useMemoryStore.getState().app,
      id: "app_live",
      api_keys: [],
    };
    const livePolicy = {
      ...useMemoryStore.getState().policy,
      id: "pol_live",
    };
    const liveMigration = {
      ...useMemoryStore.getState().migration,
      id: "mig_live",
      status: "preview",
    };
    const liveMember = {
      ...useMemoryStore.getState().team[0],
      id: "tm_live",
    };
    apiMock.getApps.mockResolvedValue([liveApp]);
    apiMock.getPolicy.mockResolvedValue(livePolicy);
    apiMock.getMigration.mockResolvedValue(liveMigration);
    const pendingInvite = {
      id: "tmi_pending",
      email: "pending@example.com",
      role: "Support",
      created_by: "owner@example.com",
      created_at: "2026-07-22T00:00:00Z",
      expires_at: "2026-07-29T00:00:00Z",
      accepted_at: null,
    };
    apiMock.getTeam.mockResolvedValue({
      members: [liveMember],
      pending_invites: [pendingInvite],
    });

    await useMemoryStore.getState().hydrate();

    const state = useMemoryStore.getState();
    expect(state.dataMode).toBe("live");
    expect(state.backendReachable).toBe(true);
    expect(state.memories).toEqual([]);
    expect(state.app.id).toBe("app_live");
    expect(state.policy).toEqual(livePolicy);
    expect(state.migration).toEqual(liveMigration);
    expect(state.team).toEqual([liveMember]);
    expect(state.pendingInvites).toEqual([pendingInvite]);
  });

  it("does not enter live mode when the core memory read fails", async () => {
    apiMock.getMemories.mockRejectedValue(new Error("memory read failed"));

    await useMemoryStore.getState().hydrate();

    expect(useMemoryStore.getState().dataMode).toBe("offline-demo");
    expect(useMemoryStore.getState().backendReachable).toBe(false);
  });
});

describe("authoritative mutations", () => {
  it("replaces the edited source record when the backend creates a new version id", async () => {
    activateLive();
    const source = useMemoryStore.getState().memories[0];
    const replacement = {
      ...source,
      id: "mem_new_version",
      content: "Updated server version",
      version: source.version + 1,
      supersedes: source.id,
    };
    apiMock.patchMemory.mockResolvedValue(replacement);

    await useMemoryStore.getState().editMemory(source.id, replacement.content);

    expect(useMemoryStore.getState().memories).not.toContainEqual(source);
    expect(useMemoryStore.getState().memories).toContainEqual(replacement);
  });

  it("removes a successfully tombstoned memory from the live list", async () => {
    activateLive();
    const source = useMemoryStore.getState().memories[0];
    apiMock.deleteMemory.mockResolvedValue({
      ...source,
      status: "deleted",
    });

    await useMemoryStore.getState().deleteMemory(source.id);

    expect(useMemoryStore.getState().memories).not.toContainEqual(
      expect.objectContaining({ id: source.id }),
    );
  });

  it("rejects offline writes without changing local state", async () => {
    useMemoryStore.setState({ hydrated: true, dataMode: "offline-demo" });
    const before = useMemoryStore.getState().memories;

    await expect(
      useMemoryStore.getState().editMemory(before[0].id, "offline edit"),
    ).rejects.toBeInstanceOf(BackendUnavailableError);
    expect(useMemoryStore.getState().memories).toEqual(before);
    expect(apiMock.patchMemory).not.toHaveBeenCalled();
  });

  it("preserves prior state for every failed server-backed mutation family", async () => {
    activateLive();
    const initial = useMemoryStore.getState();
    const memory = initial.memories[0];
    const failure = new Error("backend failed");

    apiMock.setUserConsent.mockRejectedValueOnce(failure);
    await expect(initial.toggleMemoryEnabled()).rejects.toThrow("backend failed");
    expect(useMemoryStore.getState().currentUser).toEqual(initial.currentUser);

    apiMock.patchMemory.mockRejectedValue(failure);
    await expect(initial.editMemory(memory.id, "failed edit")).rejects.toThrow();
    await expect(initial.setMemoryStatus(memory.id, "archived")).rejects.toThrow();
    expect(useMemoryStore.getState().memories).toEqual(initial.memories);

    apiMock.deleteMemory.mockRejectedValueOnce(failure);
    await expect(initial.deleteMemory(memory.id)).rejects.toThrow();
    expect(useMemoryStore.getState().memories).toEqual(initial.memories);

    apiMock.ingestEvent.mockRejectedValueOnce(failure);
    await expect(initial.addMemory("failed add", "preference")).rejects.toThrow();
    expect(useMemoryStore.getState().memories).toEqual(initial.memories);

    apiMock.upsertPolicy.mockRejectedValueOnce(failure);
    await expect(initial.togglePortabilityAxis("cross_model")).rejects.toThrow();
    expect(useMemoryStore.getState().policy).toEqual(initial.policy);

    apiMock.previewMigration.mockRejectedValueOnce(failure);
    await expect(initial.executeMigration()).rejects.toThrow();
    expect(useMemoryStore.getState().migration).toEqual(initial.migration);

    apiMock.deleteUser.mockRejectedValueOnce(failure);
    await expect(initial.deleteAllMemories()).rejects.toThrow();
    expect(useMemoryStore.getState().memories).toEqual(initial.memories);
  });

  it("uses response bodies as the only source for policy and migration state", async () => {
    activateLive();
    const serverPolicy = {
      ...useMemoryStore.getState().policy,
      id: "pol_server",
      portability: {
        ...useMemoryStore.getState().policy.portability,
        cross_model: false,
      },
    };
    const serverMigration = {
      ...useMemoryStore.getState().migration,
      id: "mig_server",
      status: "completed",
      selected_memory_ids: ["mem_server"],
    };
    apiMock.upsertPolicy.mockResolvedValue(serverPolicy);
    apiMock.previewMigration.mockResolvedValue({ migration_id: "mig_server" });
    apiMock.executeMigration.mockResolvedValue(serverMigration);

    const policyResult = await useMemoryStore
      .getState()
      .togglePortabilityAxis("cross_model");
    const migrationResult = await useMemoryStore.getState().executeMigration();

    expect(policyResult).toEqual(serverPolicy);
    expect(useMemoryStore.getState().policy).toEqual(serverPolicy);
    expect(migrationResult).toEqual(serverMigration);
    expect(useMemoryStore.getState().migration).toEqual(serverMigration);
  });

  it("uses one atomic delete-user request for delete-all", async () => {
    activateLive();
    apiMock.deleteUser.mockResolvedValue({
      user_id: useMemoryStore.getState().currentUser.id,
      tombstoned_memories: useMemoryStore.getState().memories.length,
      hms_bank_deleted: true,
      passport_status: "deleted",
    });

    const result = await useMemoryStore.getState().deleteAllMemories();

    expect(result.passport_status).toBe("deleted");
    expect(apiMock.deleteUser).toHaveBeenCalledTimes(1);
    expect(apiMock.deleteMemory).not.toHaveBeenCalled();
    expect(useMemoryStore.getState().memories).toEqual([]);
  });

  it("does not repeat an idempotent consent value", async () => {
    activateLive();
    const user = useMemoryStore.getState().currentUser;

    const result = await useMemoryStore
      .getState()
      .setMemoryEnabled(user.memory_enabled);

    expect(result).toEqual(user);
    expect(apiMock.setUserConsent).not.toHaveBeenCalled();
  });
});

describe("Quickstart", () => {
  it("advances each step only after a real successful response", async () => {
    activateLive();
    const state = useMemoryStore.getState();
    const createdUser = { ...state.currentUser, id: "usr_server" };

    apiMock.createUser.mockRejectedValueOnce(new Error("no user"));
    await expect(state.createTestUser()).rejects.toThrow();
    expect(useMemoryStore.getState().quickstart.testUserCreated).toBe(false);
    apiMock.createUser.mockResolvedValue(createdUser);
    await state.createTestUser();
    expect(useMemoryStore.getState().quickstart.testUserCreated).toBe(true);

    apiMock.ingestEvent.mockRejectedValueOnce(new Error("no ingest"));
    await expect(state.runTestEvent()).rejects.toThrow();
    expect(useMemoryStore.getState().quickstart.firstEventSent).toBe(false);
    apiMock.ingestEvent.mockResolvedValue({ event_id: "evt_server", results: [] });
    apiMock.getMemories.mockResolvedValue([]);
    await state.runTestEvent();
    expect(useMemoryStore.getState().quickstart.firstEventSent).toBe(true);

    apiMock.retrieveMemories.mockRejectedValueOnce(new Error("no retrieve"));
    await expect(state.runRetrieveTest()).rejects.toThrow();
    expect(useMemoryStore.getState().quickstart.firstRetrieveDone).toBe(false);
    apiMock.retrieveMemories.mockResolvedValue({ trace_id: "trc_server", results: [] });
    const trace = {
      id: "trc_server",
      query: "What should Luna remember about me?",
      caller: { model: "quickstart-test" },
      hms_results: { results: [] },
      projected: { results: [] },
      retrieval_events: { events: {} },
      feedback: null,
      created_at: "2026-07-22T00:00:00Z",
    };
    apiMock.getTrace.mockResolvedValue(trace);
    await state.runRetrieveTest();
    expect(useMemoryStore.getState().quickstart.firstRetrieveDone).toBe(true);
    expect(useMemoryStore.getState().lastTraceId).toBe("trc_server");
    expect(useMemoryStore.getState().lastTrace).toEqual(trace);
    expect(apiMock.getTrace).toHaveBeenCalledWith("trc_server");
  });
});

describe("console operation results", () => {
  it("returns usable app, key, team, feedback, device, and export results", async () => {
    activateLive();
    const state = useMemoryStore.getState();
    const createdApp = {
      app: { ...state.app, id: "app_created" },
      api_key: { ...state.app.api_keys[0], id: "key_created", key: "mp_secret" },
    };
    const createdKey = { ...createdApp.api_key, id: "key_second" };
    const rotatedKey = { ...createdApp.api_key, id: "key_rotated" };
    const invited = { invite: { id: "tmi_1" }, token: "invite-token" };
    const trace = { id: "trc_1", feedback: { category: "useful" } };
    const registered = { device: { ...state.devices[0], id: "dev_new" }, pairing_code: "123" };
    const bound = { ...registered.device, status: "bound" };
    const unbound = { ...registered.device, status: "unbound" };
    const wiped = { device: { ...registered.device, status: "wiped" }, tombstoned_memories: 1 };
    const blob = new Blob(["export"]);
    apiMock.createApp.mockResolvedValue(createdApp);
    apiMock.createApiKey.mockResolvedValue(createdKey);
    apiMock.rotateApiKey.mockResolvedValue(rotatedKey);
    apiMock.inviteTeamMember.mockResolvedValue(invited);
    apiMock.getTeam.mockResolvedValue({ members: state.team, pending_invites: [] });
    apiMock.recordTraceFeedback.mockResolvedValue(trace);
    apiMock.registerDevice.mockResolvedValue(registered);
    apiMock.bindDevice.mockResolvedValue(bound);
    apiMock.unbindDevice.mockResolvedValue(unbound);
    apiMock.wipeDevice.mockResolvedValue(wiped);
    apiMock.createExport.mockResolvedValue({ export_id: "exp_1" });
    apiMock.getExportStatus.mockResolvedValue({
      export_id: "exp_1",
      status: "completed",
      download_url: "/v1/exports/exp_1/download?token=once",
    });
    apiMock.downloadExport.mockResolvedValue(blob);

    expect(await state.createApp({
      name: "Created",
      product_type: "software",
      environment: "sandbox",
      data_region: "us-east-1",
      show_powered_by: true,
    })).toEqual(createdApp);
    expect(useMemoryStore.getState().app.api_keys[0].key).not.toBe("mp_secret");
    expect(useMemoryStore.getState().app.api_keys[0].key).toContain("••••");
    expect(await state.createApiKey("app_created", {
      label: "Second",
      environment: "sandbox",
    })).toEqual(createdKey);
    expect(useMemoryStore.getState().app.api_keys.at(-1)?.key).not.toBe(createdKey.key);
    expect(await state.rotateApiKey("app_created", "key_second")).toEqual(rotatedKey);
    expect(useMemoryStore.getState().app.api_keys.at(-1)?.key).not.toBe(rotatedKey.key);
    expect(await state.inviteTeamMember({ email: "new@example.com", role: "Support" })).toEqual(invited);
    expect(await state.recordTraceFeedback("trc_1", {
      memory_id: "mem_1",
      category: "useful",
    })).toEqual(trace);
    expect(await state.registerDevice({
      model: "Luna",
      generation: "v2",
      serial_number_hash: "hash",
    })).toEqual(registered);
    expect(await state.bindDevice({
      device_id: "dev_new",
      user_id: state.currentUser.id,
      pairing_code: "123",
    })).toEqual(bound);
    expect(await state.unbindDevice("dev_new")).toEqual(unbound);
    expect(await state.wipeDevice("dev_new")).toEqual(wiped);
    expect(await state.exportMemories()).toEqual({ export_id: "exp_1", blob });
  });

  it("preserves a successfully issued invite when the follow-up team refresh fails", async () => {
    activateLive();
    const state = useMemoryStore.getState();
    const invited = {
      invite: {
        id: "tmi_refresh_failure",
        email: "issued@example.com",
        role: "Support",
        created_by: "owner@example.com",
        created_at: "2026-07-22T00:00:00Z",
        expires_at: "2026-07-29T00:00:00Z",
        accepted_at: null,
      },
      token: "issued-token",
    };
    apiMock.inviteTeamMember.mockResolvedValue(invited);
    apiMock.getTeam.mockRejectedValue(new Error("refresh failed"));

    await expect(
      state.inviteTeamMember({ email: "issued@example.com", role: "Support" }),
    ).resolves.toEqual(invited);
    expect(useMemoryStore.getState().pendingInvites).toContainEqual(invited.invite);
  });
});
