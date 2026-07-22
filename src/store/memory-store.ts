"use client";

import { create } from "zustand";

import {
  api,
  type ApiKeyCreateInput,
  type AppCreateInput,
  type DeviceBindInput,
  type DeviceRegisterInput,
  type TeamInviteInput,
  type TraceFeedbackInput,
} from "@/lib/api-client";
import {
  agent,
  agents,
  app as seedApp,
  auditLogs as seedAuditLogs,
  dashboardAlerts,
  devices as seedDevices,
  kpis,
  memoryPolicy as seedPolicy,
  relationship as seedRel,
  seedMemories,
  seedMigration,
  teamMembers,
  tenant,
  user,
  allUsers,
  activitySeries,
} from "@/lib/mock-data";
import type {
  ApiKey,
  App,
  AppCreateResult,
  AppDetail,
  AuditLog,
  DebugTrace,
  DeleteUserResult,
  Device,
  DeviceRegisterResult,
  DeviceWipeResult,
  MemoryPolicy,
  MemoryRecord,
  MemoryStatus,
  Migration,
  OldDeviceAccess,
  Portability,
  TeamInviteCreateResult,
  User,
} from "@/lib/types";

export type DataMode = "loading" | "live" | "offline-demo";

export class BackendUnavailableError extends Error {
  readonly code = "backend_unavailable";

  constructor() {
    super("The backend is unavailable; demo data is read-only.");
    this.name = "BackendUnavailableError";
  }
}

interface QuickstartState {
  apiKeyCreated: boolean;
  testUserCreated: boolean;
  firstEventSent: boolean;
  firstRetrieveDone: boolean;
}

interface ExportResult {
  export_id: string;
  blob: Blob;
}

interface MemoryStore {
  tenant: typeof tenant;
  app: App;
  agents: typeof agents;
  users: User[];
  currentUser: User;
  devices: Device[];
  relationship: typeof seedRel;
  memories: MemoryRecord[];
  policy: MemoryPolicy;
  migration: Migration;
  team: typeof teamMembers;
  auditLogs: AuditLog[];
  alerts: typeof dashboardAlerts;
  kpis: typeof kpis;
  activity: typeof activitySeries;
  quickstart: QuickstartState;

  hydrated: boolean;
  backendReachable: boolean;
  dataMode: DataMode;
  hydrate: () => Promise<void>;

  environment: "sandbox" | "production";
  setEnvironment: (environment: "sandbox" | "production") => void;

  setMemoryEnabled: (enabled: boolean) => Promise<User>;
  toggleMemoryEnabled: () => Promise<User>;
  togglePortabilityAxis: (axis: keyof Portability) => Promise<MemoryPolicy>;
  setMaxMemoriesPerResponse: (value: number) => Promise<MemoryPolicy>;
  toggleSensitiveInPrompt: () => Promise<MemoryPolicy>;

  editMemory: (id: string, content: string) => Promise<MemoryRecord>;
  setMemoryStatus: (id: string, status: MemoryStatus) => Promise<MemoryRecord>;
  deleteMemory: (id: string) => Promise<MemoryRecord>;
  addMemory: (
    content: string,
    type: MemoryRecord["type"],
  ) => Promise<{ event_id: string; results: { id: string; action: string }[] }>;

  runTestEvent: () => Promise<{
    event_id: string;
    results: { id: string; action: string }[];
  } | null>;
  runRetrieveTest: () => Promise<{
    trace_id: string;
    results: unknown[];
  } | null>;
  createTestUser: () => Promise<User>;

  selectMigrationMemory: (id: string, selected: boolean) => void;
  setOldDeviceAccess: (access: OldDeviceAccess) => void;
  executeMigration: () => Promise<Migration>;
  resetMigration: () => void;
  deleteAllMemories: () => Promise<DeleteUserResult>;

  createApp: (input: AppCreateInput) => Promise<AppCreateResult>;
  createApiKey: (appId: string, input: ApiKeyCreateInput) => Promise<ApiKey>;
  rotateApiKey: (appId: string, keyId: string) => Promise<ApiKey>;
  inviteTeamMember: (input: TeamInviteInput) => Promise<TeamInviteCreateResult>;
  recordTraceFeedback: (
    traceId: string,
    input: TraceFeedbackInput,
  ) => Promise<DebugTrace>;
  registerDevice: (input: DeviceRegisterInput) => Promise<DeviceRegisterResult>;
  bindDevice: (input: DeviceBindInput) => Promise<Device>;
  unbindDevice: (deviceId: string) => Promise<Device>;
  wipeDevice: (deviceId: string) => Promise<DeviceWipeResult>;
  exportMemories: () => Promise<ExportResult>;

  getMemory: (id: string) => MemoryRecord | undefined;
  memoriesByType: () => Record<string, MemoryRecord[]>;
}

const initialQuickstart: QuickstartState = {
  apiKeyCreated: true,
  testUserCreated: false,
  firstEventSent: false,
  firstRetrieveDone: false,
};

function requireLive(state: MemoryStore): void {
  if (state.dataMode !== "live" || !state.backendReachable) {
    throw new BackendUnavailableError();
  }
}

function appDetailToApp(detail: AppDetail): App {
  return {
    ...detail,
    api_keys: detail.api_keys.map((key) => ({
      ...key,
      key: key.masked_key,
    })),
  };
}

function replaceMemory(list: MemoryRecord[], replacement: MemoryRecord): MemoryRecord[] {
  return list.map((memory) =>
    memory.id === replacement.id ? replacement : memory,
  );
}

function replaceDevice(list: Device[], replacement: Device): Device[] {
  const exists = list.some((device) => device.id === replacement.id);
  return exists
    ? list.map((device) => (device.id === replacement.id ? replacement : device))
    : [...list, replacement];
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

export const useMemoryStore = create<MemoryStore>((set, get) => ({
  tenant,
  app: seedApp,
  agents,
  users: allUsers,
  currentUser: user,
  devices: seedDevices,
  relationship: seedRel,
  memories: seedMemories,
  policy: seedPolicy,
  migration: seedMigration,
  team: teamMembers,
  auditLogs: seedAuditLogs,
  alerts: dashboardAlerts,
  kpis,
  activity: activitySeries,
  quickstart: initialQuickstart,

  hydrated: false,
  backendReachable: false,
  dataMode: "loading",

  hydrate: async () => {
    if (get().hydrated) return;
    let reachable = false;
    try {
      reachable = await api.ping();
    } catch {
      reachable = false;
    }
    if (!reachable) {
      set({
        hydrated: true,
        backendReachable: false,
        dataMode: "offline-demo",
      });
      return;
    }

    let memories: MemoryRecord[];
    try {
      memories = await api.getMemories();
    } catch {
      set({
        hydrated: true,
        backendReachable: false,
        dataMode: "offline-demo",
      });
      return;
    }

    const [appsResult, auditResult, usageResult, policyResult, migrationResult, teamResult] =
      await Promise.allSettled([
        api.getApps(),
        api.getAuditLogs(),
        api.getUsage(),
        api.getPolicy(seedApp.id, agent.id),
        api.getMigration(seedMigration.id),
        api.getTeam(),
      ]);

    set((state) => {
      const next: Partial<MemoryStore> = {
        hydrated: true,
        backendReachable: true,
        dataMode: "live",
        memories,
      };
      if (appsResult.status === "fulfilled" && appsResult.value.length > 0) {
        next.app = appDetailToApp(appsResult.value[0]);
      }
      if (auditResult.status === "fulfilled") {
        next.auditLogs = auditResult.value;
      }
      if (usageResult.status === "fulfilled") {
        const usage = usageResult.value;
        next.kpis = {
          ...state.kpis,
          memoryMau: usage.memory_mau,
          memoryOps:
            usage.ops.ingest +
            usage.ops.retrieve +
            usage.ops.update +
            usage.ops.delete,
        };
      }
      if (policyResult.status === "fulfilled" && policyResult.value) {
        next.policy = policyResult.value;
      }
      if (migrationResult.status === "fulfilled" && migrationResult.value) {
        next.migration = migrationResult.value;
      }
      if (teamResult.status === "fulfilled") {
        next.team = teamResult.value.members;
      }
      return next;
    });
  },

  environment: "sandbox",
  setEnvironment: (environment) => set({ environment }),

  setMemoryEnabled: async (enabled) => {
    const state = get();
    requireLive(state);
    if (state.currentUser.memory_enabled === enabled) return state.currentUser;
    const updated = await api.setUserConsent(state.currentUser.id, enabled);
    set((current) => ({
      currentUser: updated,
      users: current.users.map((candidate) =>
        candidate.id === updated.id ? updated : candidate,
      ),
    }));
    return updated;
  },

  toggleMemoryEnabled: async () =>
    get().setMemoryEnabled(!get().currentUser.memory_enabled),

  togglePortabilityAxis: async (axis) => {
    const state = get();
    requireLive(state);
    if (axis === "layer") {
      throw new Error("portability layer cannot be toggled as a boolean axis");
    }
    if (axis === "cross_brand_app" && !state.policy.portability.cross_brand_app) {
      return state.policy;
    }
    const portability = {
      ...state.policy.portability,
      [axis]: !state.policy.portability[axis],
    };
    const updated = await api.upsertPolicy({
      app_id: state.policy.app_id,
      agent_id: state.policy.agent_id,
      portability,
      retrieval: state.policy.retrieval,
    });
    set({ policy: updated });
    return updated;
  },

  setMaxMemoriesPerResponse: async (value) => {
    const state = get();
    requireLive(state);
    const updated = await api.upsertPolicy({
      app_id: state.policy.app_id,
      agent_id: state.policy.agent_id,
      portability: state.policy.portability,
      retrieval: {
        ...state.policy.retrieval,
        max_memories_per_response: value,
      },
    });
    set({ policy: updated });
    return updated;
  },

  toggleSensitiveInPrompt: async () => {
    const state = get();
    requireLive(state);
    const updated = await api.upsertPolicy({
      app_id: state.policy.app_id,
      agent_id: state.policy.agent_id,
      portability: state.policy.portability,
      retrieval: {
        ...state.policy.retrieval,
        include_sensitive_in_prompt:
          !state.policy.retrieval.include_sensitive_in_prompt,
      },
    });
    set({ policy: updated });
    return updated;
  },

  editMemory: async (id, content) => {
    requireLive(get());
    const updated = await api.patchMemory(id, { content });
    set((state) => ({ memories: replaceMemory(state.memories, updated) }));
    return updated;
  },

  setMemoryStatus: async (id, status) => {
    requireLive(get());
    const updated = await api.patchMemory(id, { status });
    set((state) => ({ memories: replaceMemory(state.memories, updated) }));
    return updated;
  },

  deleteMemory: async (id) => {
    requireLive(get());
    const updated = await api.deleteMemory(id);
    set((state) => ({ memories: replaceMemory(state.memories, updated) }));
    return updated;
  },

  addMemory: async (content) => {
    const state = get();
    requireLive(state);
    const outcome = await api.ingestEvent({
      user_id: state.currentUser.id,
      agent_id: agent.id,
      relationship_id: state.relationship.id,
      source_type: "explicit_instruction",
      content,
      quote: content,
    });
    const memories = await api.getMemories(state.currentUser.id);
    set({ memories });
    return outcome;
  },

  createTestUser: async () => {
    const state = get();
    requireLive(state);
    if (state.quickstart.testUserCreated) return state.currentUser;
    const created = await api.createUser({
      app_id: state.app.id,
      external_user_id: state.currentUser.external_user_id,
      age_group: state.currentUser.age_group,
      region: state.currentUser.region,
      display_name: state.currentUser.display_name,
    });
    set((current) => ({
      currentUser: created,
      users: current.users.some((candidate) => candidate.id === created.id)
        ? current.users.map((candidate) =>
            candidate.id === created.id ? created : candidate,
          )
        : [...current.users, created],
      quickstart: { ...current.quickstart, testUserCreated: true },
    }));
    return created;
  },

  runTestEvent: async () => {
    const state = get();
    requireLive(state);
    if (state.quickstart.firstEventSent) return null;
    const outcome = await api.ingestEvent({
      user_id: state.currentUser.id,
      agent_id: agent.id,
      relationship_id: state.relationship.id,
      source_type: "explicit_instruction",
      content: "I like test events to confirm the integration works.",
    });
    const memories = await api.getMemories(state.currentUser.id);
    set((current) => ({
      memories,
      quickstart: {
        ...current.quickstart,
        firstEventSent: true,
        testUserCreated: true,
      },
    }));
    return outcome;
  },

  runRetrieveTest: async () => {
    const state = get();
    requireLive(state);
    if (state.quickstart.firstRetrieveDone) return null;
    const outcome = await api.retrieveMemories({
      user_id: state.currentUser.id,
      agent_id: agent.id,
      relationship_id: state.relationship.id,
      query: "What should Luna remember about me?",
      model: "quickstart-test",
    });
    set((current) => ({
      quickstart: { ...current.quickstart, firstRetrieveDone: true },
    }));
    return outcome;
  },

  selectMigrationMemory: (id, selected) =>
    set((state) => {
      const migration = state.migration;
      const alreadySelected = migration.selected_memory_ids.includes(id);
      if (selected && !alreadySelected) {
        return {
          migration: {
            ...migration,
            selected_memory_ids: [...migration.selected_memory_ids, id],
            skipped_memory_ids: migration.skipped_memory_ids.filter(
              (candidate) => candidate !== id,
            ),
          },
        };
      }
      if (!selected && alreadySelected) {
        return {
          migration: {
            ...migration,
            selected_memory_ids: migration.selected_memory_ids.filter(
              (candidate) => candidate !== id,
            ),
          },
        };
      }
      return {};
    }),

  setOldDeviceAccess: (access) =>
    set((state) => ({
      migration: { ...state.migration, old_device_access: access },
    })),

  executeMigration: async () => {
    const state = get();
    requireLive(state);
    const preview = await api.previewMigration({
      user_id: state.currentUser.id,
      source_relationship_id: state.migration.source_relationship_id,
      target_relationship_id: state.migration.target_relationship_id,
      source_device_id: state.migration.source_device_id,
      target_device_id: state.migration.target_device_id,
    });
    const completed = await api.executeMigration({
      migration_id: preview.migration_id,
      selected_memory_ids: state.migration.selected_memory_ids,
      old_device_access: state.migration.old_device_access,
    });
    set({ migration: completed });
    return completed;
  },

  resetMigration: () =>
    set((state) => ({
      migration: {
        ...state.migration,
        status: "draft",
        selected_memory_ids: [],
        skipped_memory_ids: [],
        failed_memory_ids: [],
        completed_at: null,
        rolled_back_at: null,
      },
    })),

  deleteAllMemories: async () => {
    const state = get();
    requireLive(state);
    const result = await api.deleteUser(state.currentUser.id);
    set((current) => ({
      memories: [],
      currentUser: {
        ...current.currentUser,
        memory_enabled: false,
        passport_status: result.passport_status,
      },
      users: current.users.map((candidate) =>
        candidate.id === result.user_id
          ? {
              ...candidate,
              memory_enabled: false,
              passport_status: result.passport_status,
            }
          : candidate,
      ),
    }));
    return result;
  },

  createApp: async (input) => {
    requireLive(get());
    const result = await api.createApp(input);
    set({ app: { ...result.app, api_keys: [result.api_key] } });
    return result;
  },

  createApiKey: async (appId, input) => {
    requireLive(get());
    const created = await api.createApiKey(appId, input);
    set((state) => ({
      app:
        state.app.id === appId
          ? { ...state.app, api_keys: [...state.app.api_keys, created] }
          : state.app,
    }));
    return created;
  },

  rotateApiKey: async (appId, keyId) => {
    requireLive(get());
    const replacement = await api.rotateApiKey(appId, keyId);
    set((state) => ({
      app:
        state.app.id === appId
          ? {
              ...state.app,
              api_keys: [
                ...state.app.api_keys.filter((key) => key.id !== keyId),
                replacement,
              ],
            }
          : state.app,
    }));
    return replacement;
  },

  inviteTeamMember: async (input) => {
    requireLive(get());
    const result = await api.inviteTeamMember(input);
    const team = await api.getTeam();
    set({ team: team.members });
    return result;
  },

  recordTraceFeedback: async (traceId, input) => {
    requireLive(get());
    return api.recordTraceFeedback(traceId, input);
  },

  registerDevice: async (input) => {
    requireLive(get());
    const result = await api.registerDevice(input);
    set((state) => ({
      devices: replaceDevice(state.devices, result.device),
    }));
    return result;
  },

  bindDevice: async (input) => {
    requireLive(get());
    const result = await api.bindDevice(input);
    set((state) => ({ devices: replaceDevice(state.devices, result) }));
    return result;
  },

  unbindDevice: async (deviceId) => {
    requireLive(get());
    const result = await api.unbindDevice(deviceId);
    set((state) => ({ devices: replaceDevice(state.devices, result) }));
    return result;
  },

  wipeDevice: async (deviceId) => {
    requireLive(get());
    const result = await api.wipeDevice(deviceId);
    set((state) => ({
      devices: replaceDevice(state.devices, result.device),
    }));
    return result;
  },

  exportMemories: async () => {
    const state = get();
    requireLive(state);
    const created = await api.createExport(state.currentUser.id);
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const status = await api.getExportStatus(created.export_id);
      if (status.status === "completed") {
        const blob = await api.downloadExport(status.download_url);
        return { export_id: created.export_id, blob };
      }
      if (status.status === "failed") {
        throw new Error(status.error ?? "export failed");
      }
      await delay(250);
    }
    throw new Error("export did not complete before the polling deadline");
  },

  getMemory: (id) => get().memories.find((memory) => memory.id === id),

  memoriesByType: () =>
    get().memories.reduce<Record<string, MemoryRecord[]>>((groups, memory) => {
      (groups[memory.type] = groups[memory.type] ?? []).push(memory);
      return groups;
    }, {}),
}));
