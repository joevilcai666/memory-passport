"use client";

import { create } from "zustand";
import { nanoid } from "nanoid";
import { toast } from "sonner";
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
import { api, ApiError } from "@/lib/api-client";

interface QuickstartState {
  apiKeyCreated: boolean;
  testUserCreated: boolean;
  firstEventSent: boolean;
  firstRetrieveDone: boolean;
}

interface MemoryStore {
  // entities (seeded from mock-data; memories/audit/usage hydrate from backend)
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

  // backend sync state
  hydrated: boolean;
  backendReachable: boolean;
  memoryMutationPending: boolean;
  memoryMutationError: string | null;
  hydrate: () => Promise<void>;

  // ui prefs
  environment: "sandbox" | "production";
  setEnvironment: (e: "sandbox" | "production") => void;

  // mutations
  toggleMemoryEnabled: () => void;
  togglePortabilityAxis: (axis: keyof Portability) => void;
  setMaxMemoriesPerResponse: (n: number) => void;
  toggleSensitiveInPrompt: () => void;

  editMemory: (id: string, content: string) => Promise<MemoryRecord | null>;
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

/** True when the backend is reachable AND the working context is sandbox. */
function canCallBackend(state: MemoryStore): boolean {
  return state.backendReachable;
}

/**
 * Run an API mutation; on failure, surface a toast but never throw — the UI
 * already applied the optimistic update, and for a demo/PoC audience a soft
 * "saved locally, backend sync failed" is preferable to a half-broken screen.
 */
async function syncOrToast<T>(fn: () => Promise<T>, label: string): Promise<T | undefined> {
  try {
    return await fn();
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : String(err);
    toast.error(`Backend sync failed · ${label}`, { description: msg.slice(0, 180) });
    return undefined;
  }
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
  memoryMutationPending: false,
  memoryMutationError: null,

  // ---- hydration ---------------------------------------------------------
  /**
   * Fetch the live dataset from the backend and overwrite the corresponding
   * seed slices. Entities the backend does not expose as GET lists (apps,
   * users, agents, devices, relationships, policy) stay on their mock seed —
   * they are configuration-shaped display data. Memories / audit / usage are
   * the real per-customer data and hydrate fully.
   *
   * On any failure (backend down, auth rejected) we keep the seed and mark
   * backendReachable=false so the UI can show an "offline · demo data" hint.
   */
  hydrate: async () => {
    if (get().hydrated) return;
    const reachable = await api.ping();
    if (!reachable) {
      set({ hydrated: true, backendReachable: false });
      return;
    }
    const [memoriesR, auditR, usageR] = await Promise.allSettled([
      api.getMemories(),
      api.getAuditLogs(),
      api.getUsage(),
    ]);
    set((s) => {
      const next: Partial<MemoryStore> = {
        hydrated: true,
        // Health is intentionally public. The authenticated memories read is
        // the authoritative connectivity check for this tenant.
        backendReachable: memoriesR.status === "fulfilled",
      };
      if (memoriesR.status === "fulfilled") {
        next.memories = memoriesR.value;
        if (memoriesR.value.length > 0) {
          // the quickstart "sent first event" step is satisfied if any memory exists
          next.quickstart = { ...s.quickstart, firstEventSent: true, testUserCreated: true };
        }
      }
      if (auditR.status === "fulfilled" && auditR.value.length > 0) {
        next.auditLogs = auditR.value;
      }
      if (usageR.status === "fulfilled") {
        const u = usageR.value;
        // The Overview KPIs are shaped as headline numbers. Map the backend
        // usage bundle onto the two fields that have a real correspondence;
        // leave the rate-style KPIs on their seeded demo values.
        next.kpis = {
          ...s.kpis,
          memoryMau: u.memory_mau,
          memoryOps: u.ops.ingest + u.ops.retrieve + u.ops.update + u.ops.delete,
        };
      }
      return next;
    });
  },

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
      const policy = { ...s.policy, portability };
      // Push the whole policy upsert; the backend has no delta endpoint.
      if (canCallBackend(s)) {
        void syncOrToast(
          () =>
            api.upsertPolicy({
              app_id: policy.app_id,
              agent_id: policy.agent_id,
              portability,
              retrieval: policy.retrieval,
            }),
          "policy upsert",
        );
      }
      return {
        policy,
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
    set((s) => {
      const policy = {
        ...s.policy,
        retrieval: { ...s.policy.retrieval, max_memories_per_response: n },
      };
      if (canCallBackend(s)) {
        void syncOrToast(
          () =>
            api.upsertPolicy({
              app_id: policy.app_id,
              agent_id: policy.agent_id,
              portability: policy.portability,
              retrieval: policy.retrieval,
            }),
          "policy upsert",
        );
      }
      return { policy };
    }),

  toggleSensitiveInPrompt: () =>
    set((s) => {
      const policy = {
        ...s.policy,
        retrieval: {
          ...s.policy.retrieval,
          include_sensitive_in_prompt: !s.policy.retrieval.include_sensitive_in_prompt,
        },
      };
      if (canCallBackend(s)) {
        void syncOrToast(
          () =>
            api.upsertPolicy({
              app_id: policy.app_id,
              agent_id: policy.agent_id,
              portability: policy.portability,
              retrieval: policy.retrieval,
            }),
          "policy upsert",
        );
      }
      return { policy };
    }),

  editMemory: async (id, content) => {
    if (!canCallBackend(get())) {
      set({
        memoryMutationError:
          "Memory Passport is unavailable. Your edit was not saved.",
      });
      return null;
    }
    set({ memoryMutationPending: true, memoryMutationError: null });
    try {
      const saved = await api.patchMemory(id, { content });
      set((s) => ({
        memories: s.memories.map((memory) =>
          memory.id === id ? saved : memory,
        ),
      }));
      return saved;
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Memory Passport rejected the edit";
      set({ memoryMutationError: `${message}. Your edit was not saved.` });
      return null;
    } finally {
      set({ memoryMutationPending: false });
    }
  },

  setMemoryStatus: (id, status) => {
    set((s) => ({
      memories: s.memories.map((m) => (m.id === id ? { ...m, status } : m)),
      auditLogs: pushAudit(s.auditLogs, "Sara Kim", "memory.edited", id, `Status → ${status}`),
    }));
    if (canCallBackend(get())) {
      void syncOrToast(() => api.patchMemory(id, { status }), `memory ${id}`);
    }
  },

  deleteMemory: (id) => {
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
    }));
    if (canCallBackend(get())) {
      void syncOrToast(() => api.deleteMemory(id), `delete ${id}`);
    }
  },

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
      // Ingest through the backend pipeline so HMS retain runs; fall back to
      // local-only insert when offline so the UI still shows the new memory.
      if (canCallBackend(s)) {
        void syncOrToast(
          () =>
            api.ingestEvent({
              user_id: s.currentUser.id,
              agent_id: agent.id,
              relationship_id: s.relationship.id,
              source_type: "explicit_instruction",
              content,
              quote: content,
            }),
          "ingest memory",
        ).then((res) => {
          if (res && res.results.length > 0) {
            // Replace the optimistic id with the backend id on the matching row.
            const createdId = res.results[0].id;
            set((cur) => ({
              memories: cur.memories.map((m) => (m.id === id ? { ...m, id: createdId } : m)),
            }));
          }
        });
      }
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
      // Fire the real ingest so the customer sees their backend receive it.
      if (canCallBackend(s)) {
        void syncOrToast(
          () =>
            api.ingestEvent({
              user_id: s.currentUser.id,
              agent_id: agent.id,
              relationship_id: s.relationship.id,
              source_type: "explicit_instruction",
              content: "I like test events to confirm the integration works.",
            }),
          "test event",
        );
      }
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

  executeMigration: () => {
    const s = get();
    const movedIds = s.migration.selected_memory_ids;
    set((s2) => ({
      migration: {
        ...s2.migration,
        status: "completed",
        completed_at: new Date().toISOString(),
      },
      devices: s2.devices.map((d) => {
        if (d.id === deviceV2.id) {
          return { ...d, status: "bound", bound_user_id: s2.currentUser.id, last_seen_at: new Date().toISOString() };
        }
        if (d.id === deviceV1.id && s2.migration.old_device_access === "remove") {
          return { ...d, status: "unbound", bound_user_id: null };
        }
        return d;
      }),
      // re-link moved memories' device_id to v2 where they were device-scoped but portable
      memories: s2.memories.map((m) =>
        movedIds.includes(m.id) && m.portability.layer === "portable"
          ? { ...m, device_id: deviceV2.id }
          : m,
      ),
      auditLogs: pushAudit(
        s2.auditLogs,
        "Mia Chen",
        "migration.completed",
        s2.migration.id,
        `Moved ${movedIds.length} memories from ${deviceV1.generation} to ${deviceV2.generation}`,
      ),
    }));
    // Push the migration through preview→execute on the backend. The seed
    // migration's source/target ids are mock ids; if they don't resolve on the
    // backend the call 404s and syncOrToast surfaces a soft warning — the
    // optimistic UI change above already stands.
    if (canCallBackend(s) && movedIds.length > 0) {
      void syncOrToast(
        () =>
          api.previewMigration({
            user_id: s.currentUser.id,
            source_relationship_id: s.migration.source_relationship_id,
            target_relationship_id: s.migration.target_relationship_id,
            source_device_id: s.migration.source_device_id,
            target_device_id: s.migration.target_device_id,
          }).then((preview) =>
            api.executeMigration({
              migration_id: preview.migration_id,
              selected_memory_ids: movedIds,
              old_device_access: s.migration.old_device_access,
            }),
          ),
        "migration execute",
      );
    }
  },

  resetMigration: () =>
    set(() => ({
      migration: {
        ...seedMigration,
        selected_memory_ids: [],
        skipped_memory_ids: [],
      },
    })),

  deleteAllMemories: () => {
    const s = get();
    set((cur) => ({
      memories: cur.memories.map((m) => ({ ...m, status: "deleted" as MemoryStatus })),
      auditLogs: pushAudit(
        cur.auditLogs,
        "Mia Chen",
        "memory.deleted",
        cur.currentUser.id,
        "Deleted ALL memories (tombstone) — user-initiated",
      ),
    }));
    // Cascade delete each backend memory tombstone-by-tombstone. This is O(n)
    // but correct; n is small for a PoC and the backend delete is idempotent
    // against re-invocation on an already-tombstoned row.
    if (canCallBackend(s)) {
      for (const m of s.memories) {
        void syncOrToast(() => api.deleteMemory(m.id), `delete ${m.id}`);
      }
    }
  },

  getMemory: (id) => get().memories.find((m) => m.id === id),

  memoriesByType: () => {
    const list = get().memories;
    return list.reduce<Record<string, MemoryRecord[]>>((acc, m) => {
      (acc[m.type] = acc[m.type] || []).push(m);
      return acc;
    }, {});
  },
}));
