"use client";

import { create } from "zustand";
import { nanoid } from "nanoid";
import type {
  App,
  AuditAction,
  AuditLog,
  Device,
  MemoryPolicy,
  MemoryRecord,
  MemoryStatus,
  Migration,
  OldDeviceAccess,
  Portability,
  Relationship,
  User,
} from "@/lib/types";
import {
  agent,
  agents,
  app as seedApp,
  auditLogs as seedAuditLogs,
  dashboardAlerts,
  devices as seedDevices,
  deviceV1,
  deviceV2,
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

interface QuickstartState {
  apiKeyCreated: boolean;
  testUserCreated: boolean;
  firstEventSent: boolean;
  firstRetrieveDone: boolean;
}

interface MemoryStore {
  // entities
  tenant: typeof tenant;
  app: App;
  agents: typeof agents;
  users: User[];
  currentUser: User;
  devices: Device[];
  relationship: Relationship;
  memories: MemoryRecord[];
  policy: MemoryPolicy;
  migration: Migration;
  team: typeof teamMembers;
  auditLogs: AuditLog[];
  alerts: typeof dashboardAlerts;
  kpis: typeof kpis;
  activity: typeof activitySeries;
  quickstart: QuickstartState;

  // ui prefs
  environment: "sandbox" | "production";
  setEnvironment: (e: "sandbox" | "production") => void;

  // mutations
  toggleMemoryEnabled: () => void;
  togglePortabilityAxis: (axis: keyof Portability) => void;
  setMaxMemoriesPerResponse: (n: number) => void;
  toggleSensitiveInPrompt: () => void;

  editMemory: (id: string, content: string) => void;
  setMemoryStatus: (id: string, status: MemoryStatus) => void;
  deleteMemory: (id: string) => void;
  addMemory: (content: string, type: MemoryRecord["type"]) => void;

  // quickstart actions
  runTestEvent: () => void;
  runRetrieveTest: () => void;
  createTestUser: () => void;

  // migration
  selectMigrationMemory: (id: string, selected: boolean) => void;
  setOldDeviceAccess: (a: OldDeviceAccess) => void;
  executeMigration: () => void;
  resetMigration: () => void;

  // delete all
  deleteAllMemories: () => void;

  // helpers
  getMemory: (id: string) => MemoryRecord | undefined;
  memoriesByType: () => Record<string, MemoryRecord[]>;
}

const initialQuickstart: QuickstartState = {
  apiKeyCreated: true,
  testUserCreated: false,
  firstEventSent: false,
  firstRetrieveDone: false,
};

function pushAudit(
  list: AuditLog[],
  actor: string,
  action: AuditAction,
  target: string,
  detail: string,
): AuditLog[] {
  return [
    {
      id: nanoid(10),
      tenant_id: tenant.id,
      actor,
      action,
      target,
      detail,
      timestamp: new Date().toISOString(),
    },
    ...list,
  ];
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

  environment: "sandbox",
  setEnvironment: (e) => set({ environment: e }),

  toggleMemoryEnabled: () =>
    set((s) => {
      const next = !s.currentUser.memory_enabled;
      return {
        currentUser: { ...s.currentUser, memory_enabled: next },
        auditLogs: pushAudit(
          s.auditLogs,
          "Mia Chen",
          "policy.changed",
          s.currentUser.id,
          next ? "Memory turned ON" : "Memory paused by user",
        ),
      };
    }),

  togglePortabilityAxis: (axis) =>
    set((s) => {
      const current = s.policy.portability[axis];
      // cross_brand_app stays off in V0.1 (architecture ready, narrative deferred)
      if (axis === "cross_brand_app" && !current) return {};
      const portability = { ...s.policy.portability, [axis]: !current };
      return {
        policy: { ...s.policy, portability },
        auditLogs: pushAudit(
          s.auditLogs,
          "Mia Chen",
          "policy.changed",
          s.policy.id,
          `Portability ${axis} → ${!current ? "ON" : "OFF"}`,
        ),
      };
    }),

  setMaxMemoriesPerResponse: (n) =>
    set((s) => ({
      policy: { ...s.policy, retrieval: { ...s.policy.retrieval, max_memories_per_response: n } },
    })),

  toggleSensitiveInPrompt: () =>
    set((s) => ({
      policy: {
        ...s.policy,
        retrieval: {
          ...s.policy.retrieval,
          include_sensitive_in_prompt: !s.policy.retrieval.include_sensitive_in_prompt,
        },
      },
    })),

  editMemory: (id, content) =>
    set((s) => ({
      memories: s.memories.map((m) =>
        m.id === id ? { ...m, content, version: m.version + 1 } : m,
      ),
      auditLogs: pushAudit(s.auditLogs, "Mia Chen", "memory.edited", id, "Content edited by user"),
    })),

  setMemoryStatus: (id, status) =>
    set((s) => ({
      memories: s.memories.map((m) => (m.id === id ? { ...m, status } : m)),
      auditLogs: pushAudit(s.auditLogs, "Sara Kim", "memory.edited", id, `Status → ${status}`),
    })),

  deleteMemory: (id) =>
    set((s) => ({
      memories: s.memories.map((m) =>
        m.id === id ? { ...m, status: "deleted" as MemoryStatus } : m,
      ),
      auditLogs: pushAudit(
        s.auditLogs,
        "Mia Chen",
        "memory.deleted",
        id,
        "Deleted via Memory Center (tombstone)",
      ),
    })),

  addMemory: (content, type) =>
    set((s) => {
      const id = `mem_${nanoid(6)}`;
      const ts = new Date().toISOString();
      const newMem: MemoryRecord = {
        id,
        tenant_id: tenant.id,
        app_id: s.app.id,
        passport_id: s.currentUser.passport_id,
        user_id: s.currentUser.id,
        relationship_id: s.relationship.id,
        agent_id: agent.id,
        device_id: null,
        type,
        content,
        scope: "relationship_only",
        sensitivity: "S1",
        status: "active",
        confidence: 0.9,
        portability: s.policy.portability,
        source: {
          event_id: `evt_${nanoid(6)}`,
          source_type: "explicit_instruction",
          timestamp: ts,
          quote: content,
        },
        valid_from: ts,
        expires_at: null,
        version: 1,
        supersedes: null,
        last_used_at: null,
        usage_count: 0,
        model_provenance: { created_by_model: "gpt-4o", retrieval_history: [] },
      };
      return {
        memories: [newMem, ...s.memories],
        auditLogs: pushAudit(s.auditLogs, "Mia Chen", "memory.created", id, `Auto-written: "${content.slice(0, 40)}…"`),
      };
    }),

  runTestEvent: () =>
    set((s) => {
      if (s.quickstart.firstEventSent) return {};
      const id = "mem_quickstart";
      const ts = new Date().toISOString();
      const newMem: MemoryRecord = {
        id,
        tenant_id: tenant.id,
        app_id: s.app.id,
        passport_id: s.currentUser.passport_id,
        user_id: s.currentUser.id,
        relationship_id: s.relationship.id,
        agent_id: agent.id,
        device_id: null,
        type: "preference",
        content: "You like test events to confirm the integration works.",
        scope: "relationship_only",
        sensitivity: "S1",
        status: "active",
        confidence: 0.99,
        portability: s.policy.portability,
        source: { event_id: `evt_${nanoid(6)}`, source_type: "explicit_instruction", timestamp: ts, quote: "I like test events to confirm the integration works." },
        valid_from: ts,
        expires_at: null,
        version: 1,
        supersedes: null,
        last_used_at: null,
        usage_count: 0,
        model_provenance: { created_by_model: "gpt-4o", retrieval_history: [] },
      };
      return {
        memories: [newMem, ...s.memories.filter((m) => m.id !== id)],
        quickstart: { ...s.quickstart, firstEventSent: true, testUserCreated: true },
        auditLogs: pushAudit(s.auditLogs, "SDK", "memory.created", id, "Ingest test event received"),
      };
    }),

  runRetrieveTest: () =>
    set((s) =>
      s.quickstart.firstRetrieveDone
        ? {}
        : {
            quickstart: { ...s.quickstart, firstRetrieveDone: true },
            auditLogs: pushAudit(s.auditLogs, "SDK", "memory.viewed", "retrieve-test", "Retrieve test succeeded (3 memories returned)"),
          },
    ),

  createTestUser: () =>
    set((s) =>
      s.quickstart.testUserCreated
        ? {}
        : { quickstart: { ...s.quickstart, testUserCreated: true } },
    ),

  selectMigrationMemory: (id, selected) =>
    set((s) => {
      const m = s.migration;
      const isInSelected = m.selected_memory_ids.includes(id);
      if (selected && !isInSelected) {
        return {
          migration: {
            ...m,
            selected_memory_ids: [...m.selected_memory_ids, id],
            skipped_memory_ids: m.skipped_memory_ids.filter((x) => x !== id),
          },
        };
      }
      if (!selected && isInSelected) {
        return {
          migration: {
            ...m,
            selected_memory_ids: m.selected_memory_ids.filter((x) => x !== id),
          },
        };
      }
      return {};
    }),

  setOldDeviceAccess: (a) =>
    set((s) => ({ migration: { ...s.migration, old_device_access: a } })),

  executeMigration: () =>
    set((s) => {
      const movedIds = s.migration.selected_memory_ids;
      return {
        migration: {
          ...s.migration,
          status: "completed",
          completed_at: new Date().toISOString(),
        },
        devices: s.devices.map((d) => {
          if (d.id === deviceV2.id) {
            return { ...d, status: "bound", bound_user_id: s.currentUser.id, last_seen_at: new Date().toISOString() };
          }
          if (d.id === deviceV1.id && s.migration.old_device_access === "remove") {
            return { ...d, status: "unbound", bound_user_id: null };
          }
          return d;
        }),
        // re-link moved memories' device_id to v2 where they were device-scoped but portable
        memories: s.memories.map((m) =>
          movedIds.includes(m.id) && m.portability.layer === "portable"
            ? { ...m, device_id: deviceV2.id }
            : m,
        ),
        auditLogs: pushAudit(
          s.auditLogs,
          "Mia Chen",
          "migration.completed",
          s.migration.id,
          `Moved ${movedIds.length} memories from ${deviceV1.generation} to ${deviceV2.generation}`,
        ),
      };
    }),

  resetMigration: () =>
    set(() => ({
      migration: {
        ...seedMigration,
        selected_memory_ids: [],
        skipped_memory_ids: [],
      },
    })),

  deleteAllMemories: () =>
    set((s) => ({
      memories: s.memories.map((m) => ({ ...m, status: "deleted" as MemoryStatus })),
      auditLogs: pushAudit(
        s.auditLogs,
        "Mia Chen",
        "memory.deleted",
        s.currentUser.id,
        "Deleted ALL memories (tombstone) — user-initiated",
      ),
    })),

  getMemory: (id) => get().memories.find((m) => m.id === id),

  memoriesByType: () => {
    const list = get().memories;
    return list.reduce<Record<string, MemoryRecord[]>>((acc, m) => {
      (acc[m.type] = acc[m.type] || []).push(m);
      return acc;
    }, {});
  },
}));
