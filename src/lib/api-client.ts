// ============================================================================
// Memory Passport — typed HTTP client over the FastAPI backend.
//
// Browser requests stay same-origin. The server-only MP gateway owns the
// upstream URL and tenant credential.
// Every method maps a backend endpoint to the shapes in src/lib/types.ts.
// The backend response schemas mirror types.ts 1:1 (see
// backend/app/schemas/provisioning.py — "mirror src/lib/types.ts interfaces
// exactly"); this adapter's only job is to unwrap pagination/response
// envelopes and pass the payload through.
//
// All methods throw ApiError on non-2xx so the store can catch and degrade
// to mock data without crashing the UI.
// ============================================================================

import type {
  AuditLog,
  MemoryPolicy,
  MemoryRecord,
  Migration,
  Portability,
  RetrievedMemoryish,
  UsageBundle,
} from "@/lib/types";

const BASE_URL = "/api/mp";

/** Raised on any non-2xx backend response, or on a network failure. */
export class ApiError extends Error {
  readonly status: number | null;
  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// --- raw fetch -------------------------------------------------------------

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  // Keep every browser request on the product origin. Accepting absolute URLs
  // here would let future callers silently bypass the server-only gateway.
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new ApiError(`Memory Passport path must be same-origin: ${path}`);
  }
  const url = `${BASE_URL}${path}`;
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let res: Response;
  try {
    res = await fetch(url, { ...init, headers, cache: "no-store" });
  } catch (err) {
    // Network-level failure reaching the same-origin product gateway.
    throw new ApiError(
      `Network error reaching Memory Passport gateway: ${
        err instanceof Error ? err.message : String(err)
      }`,
    );
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new ApiError(
      `Memory Passport ${res.status} ${res.statusText} for ${path}${
        detail ? ` — ${detail.slice(0, 200)}` : ""
      }`,
      res.status,
    );
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- response envelopes ----------------------------------------------------

interface MemoryListResponse {
  items: MemoryRecord[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
interface RetrieveResponse {
  trace_id: string;
  results: RetrievedMemoryish[];
}
interface UsageResponse {
  since: string;
  until: string;
  memory_mau: number;
  memory_ops: { ingest: number; retrieve: number; update: number; delete: number };
  storage: number;
  device_activations: number;
  migration_count: number;
}

// --- request bodies --------------------------------------------------------

export interface IngestEventInput {
  user_id: string;
  agent_id: string;
  relationship_id: string;
  source_type: string;
  content: string;
  quote?: string;
  event_id?: string;
}
export interface RetrieveInput {
  user_id: string;
  agent_id: string;
  relationship_id: string;
  query: string;
  model?: string;
  device_id?: string;
}
export interface PolicyUpsertInput {
  app_id: string;
  agent_id: string;
  portability: Portability;
  retrieval: {
    max_memories_per_response: number;
    include_sensitive_in_prompt: boolean;
  };
}
export interface MigrationPreviewInput {
  user_id: string;
  source_relationship_id: string;
  target_relationship_id: string;
  source_device_id: string;
  target_device_id: string;
}
export interface MigrationExecuteInput {
  migration_id: string;
  selected_memory_ids: string[];
  old_device_access: "keep" | "remove";
}

// --- public API ------------------------------------------------------------

export const api = {
  BASE_URL,
  /** Quick liveness check — true when the backend answers /v1/health 200. */
  async ping(): Promise<boolean> {
    try {
      const body = await request<{ mp: string; hms: string; db: string }>(
        "/v1/health",
      );
      return body.mp === "ok";
    } catch {
      return false;
    }
  },

  // -- reads --------------------------------------------------------------

  async getMemories(userId?: string): Promise<MemoryRecord[]> {
    const qs = userId ? `?user_id=${encodeURIComponent(userId)}&page_size=100` : "?page_size=100";
    const body = await request<MemoryListResponse>(`/v1/memories${qs}`);
    return body.items;
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    const body = await request<AuditLogListResponse>(
      "/v1/audit_logs?page_size=100",
    );
    return body.items;
  },

  async getUsage(): Promise<UsageBundle> {
    const body = await request<UsageResponse>("/v1/usage");
    return {
      memory_mau: body.memory_mau,
      ops: body.memory_ops,
      storage_bytes: body.storage,
      device_activations: body.device_activations,
      migration_count: body.migration_count,
    };
  },

  async getMigration(migrationId: string): Promise<Migration | null> {
    try {
      return await request<Migration>(
        `/v1/migrations/${encodeURIComponent(migrationId)}`,
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },

  async getPolicy(): Promise<MemoryPolicy | null> {
    // The backend has no GET /v1/policies (POST-only upsert). We cannot
    // hydrate the policy from the backend; the store keeps the seed policy
    // as the live source of truth and pushes mutations via upsertPolicy.
    return null;
  },

  // -- writes -------------------------------------------------------------

  async ingestEvent(input: IngestEventInput): Promise<{ event_id: string; results: { id: string; action: string }[] }> {
    return request("/v1/events/ingest", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async retrieveMemories(
    input: RetrieveInput,
  ): Promise<{ trace_id: string; results: RetrievedMemoryish[] }> {
    const body = await request<RetrieveResponse>("/v1/memories/retrieve", {
      method: "POST",
      body: JSON.stringify(input),
    });
    return { trace_id: body.trace_id, results: body.results };
  },

  async patchMemory(
    id: string,
    patch: { content?: string; status?: string },
  ): Promise<MemoryRecord> {
    return request(`/v1/memories/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  },

  async deleteMemory(id: string): Promise<MemoryRecord> {
    return request(`/v1/memories/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  },

  async upsertPolicy(input: PolicyUpsertInput): Promise<MemoryPolicy> {
    return request("/v1/policies", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async previewMigration(
    input: MigrationPreviewInput,
  ): Promise<{
    migration_id: string;
    recommended: string[];
    needs_review: string[];
    not_moved: string[];
  }> {
    const body = await request<{
      migration_id: string;
      recommended: { memory_ids: string[] };
      needs_review: { memory_ids: string[] };
      not_moved: { memory_ids: string[] };
    }>("/v1/migrations/preview", {
      method: "POST",
      body: JSON.stringify(input),
    });
    return {
      migration_id: body.migration_id,
      recommended: body.recommended.memory_ids,
      needs_review: body.needs_review.memory_ids,
      not_moved: body.not_moved.memory_ids,
    };
  },

  async executeMigration(
    input: MigrationExecuteInput,
  ): Promise<Migration> {
    return request("/v1/migrations/execute", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async rollbackMigration(migrationId: string): Promise<Migration> {
    return request(`/v1/migrations/${encodeURIComponent(migrationId)}/rollback`, {
      method: "POST",
    });
  },
};
