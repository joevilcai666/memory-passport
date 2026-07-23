// ============================================================================
// Memory Passport — typed HTTP client over the FastAPI backend.
//
// Browser requests stay same-origin. The server-only MP gateway owns the
// upstream URL and tenant credential: it attaches the tenant API key, enforces
// a per-method endpoint allow-list, and proxies to FastAPI. This client never
// reads or sends a tenant credential and never reaches the FastAPI origin
// directly.
//
// Every method maps a backend endpoint to the shapes in src/lib/types.ts.
// The backend response schemas mirror types.ts 1:1 (see
// backend/app/schemas/provisioning.py — "mirror src/lib/types.ts interfaces
// exactly"); this adapter's only job is to unwrap pagination/response
// envelopes and pass the payload through.
//
// All methods throw ApiError on non-2xx so the store can catch and degrade
// without crashing the UI.
// ============================================================================

import type {
  ApiKey,
  AppCreateResult,
  AppDetail,
  AuditLog,
  DebugTrace,
  DeleteUserResult,
  Device,
  DeviceRegisterResult,
  DeviceWipeResult,
  Environment,
  ExportStatusResult,
  MemoryPolicy,
  MemoryRecord,
  Migration,
  Portability,
  ProductType,
  PublicTeamInvite,
  RetrievedMemoryish,
  TeamBundle,
  TeamInviteCreateResult,
  TeamRole,
  TraceFeedbackCategory,
  User,
  UsageBundle,
} from "@/lib/types";

// Same-origin product gateway. The gateway forwards to the FastAPI backend and
// attaches the tenant credential server-side; the browser never sees it.
const BASE_URL = "/api/mp";

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string | null;
  readonly detail: unknown;

  constructor(
    message: string,
    status: number | null = null,
    code: string | null = null,
    detail: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

async function apiErrorFromResponse(res: Response, path: string): Promise<ApiError> {
  let payload: unknown = null;
  try {
    payload = await res.clone().json();
  } catch {
    payload = await res.text().catch(() => "");
  }

  const root = payload && typeof payload === "object"
    ? (payload as Record<string, unknown>)
    : null;
  const rawDetail = root?.detail ?? root?.error ?? payload;
  const structured = rawDetail && typeof rawDetail === "object"
    ? (rawDetail as Record<string, unknown>)
    : null;
  const code = typeof structured?.code === "string" ? structured.code : null;
  const message =
    (typeof structured?.message === "string" && structured.message) ||
    (typeof rawDetail === "string" && rawDetail) ||
    `Backend ${res.status} ${res.statusText || "error"} for ${path}`;
  return new ApiError(message, res.status, code, rawDetail);
}

async function fetchResponse(path: string, init: RequestInit = {}): Promise<Response> {
  // Only same-origin relative paths are allowed. This prevents a client-side
  // caller from steering the gateway at an arbitrary host and keeps the tenant
  // credential strictly server-side.
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new ApiError(`Memory Passport path must be same-origin: ${path}`);
  }
  const url = `${BASE_URL}${path}`;
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    // No Authorization header here: the server-only gateway injects the tenant
    // key when forwarding to FastAPI.
    response = await fetch(url, { ...init, headers, cache: "no-store" });
  } catch (error) {
    throw new ApiError(
      `Network error reaching Memory Passport gateway: ${
        error instanceof Error ? error.message : String(error)
      }`,
      null,
      "network_error",
    );
  }
  if (!response.ok) throw await apiErrorFromResponse(response, path);
  return response;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetchResponse(path, init);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

interface MemoryListResponse {
  items: MemoryRecord[];
}

interface AuditLogListResponse {
  items: AuditLog[];
}

interface RetrieveResponse {
  trace_id: string;
  results: RetrievedMemoryish[];
}

interface UsageResponse {
  memory_mau: number;
  memory_ops: { ingest: number; retrieve: number; update: number; delete: number };
  storage: number;
  device_activations: number;
  migration_count: number;
}

export interface AppCreateInput {
  name: string;
  product_type: ProductType;
  environment: Environment;
  data_region: "us-east-1" | "eu-west-1" | "ap-southeast-1";
  show_powered_by: boolean;
}

export interface ApiKeyCreateInput {
  label: string;
  environment: Environment;
}

export interface UserCreateInput {
  app_id: string;
  external_user_id: string;
  age_group: "adult" | "minor" | "unknown";
  region: string;
  display_name: string;
}

export interface IngestEventInput {
  user_id: string;
  agent_id: string;
  relationship_id: string;
  source_type: string;
  content: string;
  quote?: string;
  event_id?: string;
  device_id?: string;
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

export interface DeviceRegisterInput {
  model: string;
  generation: string;
  serial_number_hash: string;
}

export interface DeviceBindInput {
  device_id: string;
  user_id: string;
  pairing_code: string;
}

export interface TeamInviteInput {
  email: string;
  role: TeamRole;
}

export interface TeamInviteAcceptInput {
  name: string;
  avatar_color?: string;
}

export interface TraceFeedbackInput {
  memory_id: string;
  category: TraceFeedbackCategory;
}

export const api = {
  BASE_URL,

  async ping(): Promise<boolean> {
    try {
      const body = await request<{ mp: string }>("/v1/health");
      return body.mp === "ok";
    } catch {
      return false;
    }
  },

  async getApps(): Promise<AppDetail[]> {
    const body = await request<{ items: AppDetail[] }>("/v1/apps");
    return body.items;
  },

  async getApp(appId: string): Promise<AppDetail> {
    return request(`/v1/apps/${encodeURIComponent(appId)}`);
  },

  async createApp(input: AppCreateInput): Promise<AppCreateResult> {
    return request("/v1/apps", { method: "POST", body: JSON.stringify(input) });
  },

  async createApiKey(appId: string, input: ApiKeyCreateInput): Promise<ApiKey> {
    return request(`/v1/apps/${encodeURIComponent(appId)}/api-keys`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  // App-key rotation is a data operation authenticated by the tenant key held
  // server-side by the gateway; the returned one-time secret is surfaced to the
  // operator for their own backend integration and never becomes this client's
  // transport credential.
  async rotateApiKey(appId: string, keyId: string): Promise<ApiKey> {
    return request(
      `/v1/apps/${encodeURIComponent(appId)}/api-keys/${encodeURIComponent(keyId)}/rotate`,
      { method: "POST" },
    );
  },

  async createUser(input: UserCreateInput): Promise<User> {
    return request("/v1/users", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async getMemories(userId?: string): Promise<MemoryRecord[]> {
    const query = userId
      ? `?user_id=${encodeURIComponent(userId)}&page_size=100`
      : "?page_size=100";
    const body = await request<MemoryListResponse>(`/v1/memories${query}`);
    return body.items;
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    const body = await request<AuditLogListResponse>("/v1/audit_logs?page_size=100");
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
      return await request<Migration>(`/v1/migrations/${encodeURIComponent(migrationId)}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },

  async getPolicy(appId?: string, agentId?: string): Promise<MemoryPolicy | null> {
    if (!appId || !agentId) return null;
    const query = `?app_id=${encodeURIComponent(appId)}&agent_id=${encodeURIComponent(agentId)}`;
    try {
      return await request<MemoryPolicy>(`/v1/policies${query}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },

  async setUserConsent(userId: string, memoryEnabled: boolean): Promise<User> {
    return request(`/v1/users/${encodeURIComponent(userId)}/consent`, {
      method: "PATCH",
      body: JSON.stringify({ memory_enabled: memoryEnabled }),
    });
  },

  async createExport(userId: string): Promise<{ export_id: string }> {
    return request("/v1/exports", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, format: "json" }),
    });
  },

  async getExportStatus(exportId: string): Promise<ExportStatusResult> {
    return request(`/v1/exports/${encodeURIComponent(exportId)}`);
  },

  async downloadExport(downloadUrl: string | null): Promise<Blob> {
    if (!downloadUrl) {
      throw new ApiError("export is not ready for download", null, "export_not_ready");
    }
    if (!/^\/v1\/exports\/[^/?]+\/download\?/.test(downloadUrl)) {
      throw new ApiError(
        "export download path is invalid",
        null,
        "invalid_export_download_path",
      );
    }
    // The backend returns a relative token-gated path
    // (/v1/exports/{id}/download?token=…); it is same-origin-safe and proxied
    // by the gateway; the one-time query token further scopes the download.
    const response = await fetchResponse(downloadUrl);
    return response.blob();
  },

  async deleteUser(userId: string): Promise<DeleteUserResult> {
    return request("/v1/delete_user", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    });
  },

  async registerDevice(input: DeviceRegisterInput): Promise<DeviceRegisterResult> {
    return request("/v1/devices/register", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async bindDevice(input: DeviceBindInput): Promise<Device> {
    return request("/v1/devices/bind", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async unbindDevice(deviceId: string): Promise<Device> {
    return request("/v1/devices/unbind", {
      method: "POST",
      body: JSON.stringify({ device_id: deviceId }),
    });
  },

  async wipeDevice(deviceId: string): Promise<DeviceWipeResult> {
    return request("/v1/devices/wipe", {
      method: "POST",
      body: JSON.stringify({ device_id: deviceId }),
    });
  },

  async getTeam(): Promise<TeamBundle> {
    return request("/v1/team");
  },

  async inviteTeamMember(input: TeamInviteInput): Promise<TeamInviteCreateResult> {
    return request("/v1/team/invites", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async previewTeamInvite(token: string): Promise<PublicTeamInvite> {
    return request(`/v1/public/team-invites/${encodeURIComponent(token)}`);
  },

  async acceptTeamInvite(
    token: string,
    input: TeamInviteAcceptInput,
  ): Promise<TeamBundle["members"][number]> {
    return request(`/v1/public/team-invites/${encodeURIComponent(token)}/accept`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async ingestEvent(
    input: IngestEventInput,
  ): Promise<{ event_id: string; results: { id: string; action: string }[] }> {
    return request("/v1/events/ingest", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async retrieveMemories(input: RetrieveInput): Promise<RetrieveResponse> {
    return request("/v1/memories/retrieve", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async getTrace(traceId: string): Promise<DebugTrace> {
    return request(`/v1/debug/traces/${encodeURIComponent(traceId)}`);
  },

  async recordTraceFeedback(
    traceId: string,
    input: TraceFeedbackInput,
  ): Promise<DebugTrace> {
    return request(`/v1/debug/traces/${encodeURIComponent(traceId)}/feedback`, {
      method: "POST",
      body: JSON.stringify(input),
    });
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
    return request(`/v1/memories/${encodeURIComponent(id)}`, { method: "DELETE" });
  },

  async upsertPolicy(input: PolicyUpsertInput): Promise<MemoryPolicy> {
    return request("/v1/policies", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async previewMigration(input: MigrationPreviewInput): Promise<{
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

  async executeMigration(input: MigrationExecuteInput): Promise<Migration> {
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
