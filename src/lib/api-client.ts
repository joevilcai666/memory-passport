// Typed HTTP client for the FastAPI backend.

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

const BASE_URL = process.env.NEXT_PUBLIC_MP_API_URL ?? "http://127.0.0.1:8000";
let activeApiKey =
  process.env.NEXT_PUBLIC_MP_API_KEY ??
  "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd";
let activeApiKeyId = process.env.NEXT_PUBLIC_MP_API_KEY_ID ?? "key_sb_1";

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
  const rawDetail = root?.detail ?? payload;
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
  const url = path.startsWith("http") ? path : `${BASE_URL}${path}`;
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${activeApiKey}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, { ...init, headers, cache: "no-store" });
  } catch (error) {
    throw new ApiError(
      `Network error reaching backend at ${BASE_URL}: ${
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

  configureCredential(apiKey: string, apiKeyId?: string): void {
    activeApiKey = apiKey;
    if (apiKeyId) activeApiKeyId = apiKeyId;
  },

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
    return request(`/v1/apps/${appId}`);
  },

  async createApp(input: AppCreateInput): Promise<AppCreateResult> {
    return request("/v1/apps", { method: "POST", body: JSON.stringify(input) });
  },

  async createApiKey(appId: string, input: ApiKeyCreateInput): Promise<ApiKey> {
    return request(`/v1/apps/${appId}/api-keys`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async rotateApiKey(appId: string, keyId: string): Promise<ApiKey> {
    const replacement = await request<ApiKey>(
      `/v1/apps/${appId}/api-keys/${keyId}/rotate`,
      { method: "POST" },
    );
    if (keyId === activeApiKeyId) {
      activeApiKey = replacement.key;
      activeApiKeyId = replacement.id;
    }
    return replacement;
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
      return await request<Migration>(`/v1/migrations/${migrationId}`);
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
    return request(`/v1/users/${userId}/consent`, {
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
    return request(`/v1/exports/${exportId}`);
  },

  async downloadExport(downloadUrl: string | null): Promise<Blob> {
    if (!downloadUrl) {
      throw new ApiError("export is not ready for download", null, "export_not_ready");
    }
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
    return request(`/v1/debug/traces/${traceId}`);
  },

  async recordTraceFeedback(
    traceId: string,
    input: TraceFeedbackInput,
  ): Promise<DebugTrace> {
    return request(`/v1/debug/traces/${traceId}/feedback`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async patchMemory(
    id: string,
    patch: { content?: string; status?: string },
  ): Promise<MemoryRecord> {
    return request(`/v1/memories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  },

  async deleteMemory(id: string): Promise<MemoryRecord> {
    return request(`/v1/memories/${id}`, { method: "DELETE" });
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
    return request(`/v1/migrations/${migrationId}/rollback`, { method: "POST" });
  },
};
