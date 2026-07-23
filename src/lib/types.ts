// ============================================================================
// Memory Passport — domain types
// Mirrors the data model in PRD v2.0 §7 (Tenant, App, User, Agent, Device,
// Relationship, Memory Record, Migration, AuditLog).
// ============================================================================

export type ID = string;

// ---- Tenant & App ---------------------------------------------------------

export interface Tenant {
  id: ID;
  name: string;
  plan: "Sandbox" | "Growth" | "Enterprise";
  created_at: string;
}

export type ProductType = "software" | "hardware" | "hybrid";
export type Environment = "sandbox" | "production";

export interface App {
  id: ID;
  tenant_id: ID;
  name: string;
  product_type: ProductType;
  environment: Environment;
  data_region: "us-east-1" | "eu-west-1" | "ap-southeast-1";
  show_powered_by: boolean;
  status: "active" | "paused";
  api_keys: ApiKey[];
  created_at: string;
}

export interface ApiKey {
  id: ID;
  label: string;
  environment: Environment;
  key: string; // e.g. mp_sandbox_xxx
  created_at: string;
  last_used_at: string | null;
}

// ---- Users & Agents -------------------------------------------------------

export type AgeGroup = "adult" | "minor" | "unknown";

export interface User {
  id: ID;
  external_user_id: string;
  passport_id: string; // user-ownership anchor
  passport_status?: "active" | "deleted";
  passport_deleted_at?: string | null;
  age_group: AgeGroup;
  region: string;
  memory_enabled: boolean;
  created_at: string;
  display_name: string;
  avatar_color: string;
}

export type AgentType = "character" | "companion" | "pet" | "robot" | "assistant";

export interface Agent {
  id: ID;
  app_id: ID;
  name: string;
  type: AgentType;
  persona_version: string;
  memory_policy_id: ID;
  allowed_memory_types: MemoryType[];
  created_at: string;
  emoji: string;
}

// ---- Devices --------------------------------------------------------------

export type DeviceStatus = "registered" | "bound" | "unbound" | "wiped";

export interface Device {
  id: ID;
  model: string;
  generation: string; // v1 / v2
  serial_number_hash: string;
  status: DeviceStatus;
  bound_user_id: ID | null;
  last_seen_at: string | null;
}

// ---- Relationships --------------------------------------------------------

export type RelationshipType = "companion" | "pet" | "robot" | "assistant";

export interface Relationship {
  id: ID;
  user_id: ID;
  agent_id: ID;
  device_id: ID | null;
  relationship_type: RelationshipType;
  memory_enabled: boolean;
  created_at: string;
}

// ---- Memory Record --------------------------------------------------------

export type MemoryType =
  | "profile"
  | "preference"
  | "boundary"
  | "relationship"
  | "event"
  | "task";

export type MemoryScope =
  | "user_global"
  | "relationship_only"
  | "agent_only"
  | "device_only"
  | "private"
  | "blocked";

export type MemorySensitivity = "S0" | "S1" | "S2" | "S3";
// S0 auto-write | S1 auto-write + visible | S2 user confirm | S3 block/safety

export type MemoryStatus =
  | "candidate"
  | "active"
  | "archived"
  | "needs_review"
  | "deleted"
  | "expired"
  | "flagged_wrong";

export type PortabilityLayer = "portable" | "device_local";

export interface Portability {
  layer: PortabilityLayer;
  cross_device: boolean;
  cross_role: boolean;
  cross_model: boolean;
  cross_brand_app: boolean;
}

export interface MemorySource {
  event_id: ID;
  source_type: "chat" | "voice" | "setup" | "explicit_instruction" | "robot_event" | "app_event";
  timestamp: string;
  /** The exact thing the user said/did that caused this memory — "why was this saved?" */
  quote: string;
}

export interface RetrievalEvent {
  model: string; // "gpt-4o", "claude-3.5-sonnet", etc.
  used: boolean;
  timestamp: string;
}

export interface MemoryRecord {
  id: ID;
  tenant_id: ID;
  app_id: ID;
  passport_id: string;
  user_id: ID;
  relationship_id: ID;
  agent_id: ID;
  device_id: ID | null;
  type: MemoryType;
  content: string;
  scope: MemoryScope;
  sensitivity: MemorySensitivity;
  status: MemoryStatus;
  confidence: number; // 0..1
  portability: Portability;
  source: MemorySource;
  valid_from: string;
  expires_at: string | null;
  version: number;
  supersedes: ID | null;
  last_used_at: string | null;
  usage_count: number;
  model_provenance: {
    created_by_model: string;
    retrieval_history: RetrievalEvent[];
  };
}

// ---- Memory Policy --------------------------------------------------------

export interface AutoWriteRule {
  id: ID;
  memory_type: MemoryType;
  action: "auto_write" | "confirm" | "block";
  sensitivity: MemorySensitivity;
  ttl_days: number | null; // null = no expiry
}

export interface MemoryPolicy {
  id: ID;
  app_id: ID;
  agent_id: ID;
  auto_write_rules: AutoWriteRule[];
  portability: Portability; // the 4-axis toggles
  retrieval: {
    max_memories_per_response: number;
    include_sensitive_in_prompt: boolean;
  };
}

// ---- Migration ------------------------------------------------------------

export type MigrationStatus =
  | "draft"
  | "preview"
  | "confirmed"
  | "running"
  | "completed"
  | "completed_with_warnings"
  | "failed"
  | "rolled_back";

export type OldDeviceAccess = "keep" | "remove";

export interface Migration {
  id: ID;
  user_id: ID;
  source_relationship_id: ID;
  target_relationship_id: ID;
  source_device_id: ID;
  target_device_id: ID;
  status: MigrationStatus;
  selected_memory_ids: ID[];
  skipped_memory_ids: ID[];
  failed_memory_ids: ID[];
  old_device_access: OldDeviceAccess;
  audit_log_id: ID | null;
  created_at: string;
  completed_at: string | null;
  rolled_back_at: string | null;
}

// ---- Audit Log ------------------------------------------------------------

export type AuditAction =
  | "memory.created"
  | "memory.deleted"
  | "memory.edited"
  | "memory.viewed"
  | "policy.changed"
  | "device.bound"
  | "device.unbound"
  | "migration.completed"
  | "migration.started"
  | "migration.rolled_back"
  | "memory.exported"
  | "app.created"
  | "agent.created"
  | "user.created"
  | "relationship.created"
  | "device.registered"
  | "memory.blocked"
  | "retrieval.performed"
  | "device.wiped"
  | "user.deleted";

export interface AuditLog {
  id: ID;
  tenant_id: ID;
  actor: string; // team member name
  action: AuditAction;
  target: string; // e.g. memory_id or device_id
  detail: string;
  timestamp: string;
}

// ---- Team -----------------------------------------------------------------

export type TeamRole = "Owner" | "Admin" | "Support";

export interface TeamMember {
  id: ID;
  name: string;
  email: string;
  role: TeamRole;
  avatar_color: string;
  joined_at?: string;
  last_active: string;
}

export interface ApiKeyMetadata {
  id: ID;
  label: string;
  environment: Environment;
  masked_key: string;
  created_at: string;
  last_used_at: string | null;
}

export type AppDetail = Omit<App, "api_keys"> & {
  api_keys: ApiKeyMetadata[];
};

export interface AppCreateResult {
  app: Omit<App, "api_keys">;
  api_key: ApiKey;
}

export interface ExportStatusResult {
  export_id: ID;
  status: "pending" | "running" | "completed" | "failed";
  download_url: string | null;
  expires_at: string | null;
  error: string | null;
}

export interface DeleteUserResult {
  user_id: ID;
  tombstoned_memories: number;
  hms_bank_deleted: boolean;
  passport_status: "active" | "deleted";
}

export interface DeviceRegisterResult {
  device: Device;
  pairing_code: string;
}

export interface DeviceWipeResult {
  device: Device;
  tombstoned_memories: number;
}

export interface TeamInvite {
  id: ID;
  email: string;
  role: TeamRole;
  created_by: string;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
}

export interface TeamBundle {
  members: TeamMember[];
  pending_invites: TeamInvite[];
}

export interface TeamInviteCreateResult {
  invite: TeamInvite;
  token: string;
}

export interface PublicTeamInvite {
  tenant_name: string;
  email: string;
  role: TeamRole;
  expires_at: string;
}

export type TraceFeedbackCategory =
  | "useful"
  | "not_useful"
  | "wrong_memory"
  | "should_not_have_used";

export interface TraceFeedback {
  memory_id: ID;
  category: TraceFeedbackCategory;
  actor: string;
  recorded_at: string;
}

export interface DebugTrace {
  id: ID;
  query: string;
  caller: Record<string, unknown>;
  hms_results: Record<string, unknown>;
  projected: { results: RetrievedMemoryish[] } & Record<string, unknown>;
  retrieval_events: Record<string, unknown>;
  feedback: TraceFeedback | null;
  created_at: string;
}

// ---- Alerts (Overview dashboard) -----------------------------------------

export type AlertSeverity = "warning" | "error" | "info";

export interface DashboardAlert {
  id: ID;
  severity: AlertSeverity;
  title: string;
  detail: string;
  timestamp: string;
}

// ---- Backend-derived shapes -----------------------------------------------
// These mirror the projected memory + usage payloads returned by the FastAPI
// backend. They are richer/looser than the authoritative MemoryRecord because
// retrieve() applies scope projection + masking server-side.

export interface RetrievedMemoryish {
  id: ID;
  type: string;
  content: string;
  scope: string;
  sensitivity: string;
  status: string;
  confidence: number;
  source: MemorySource | Record<string, unknown>;
  portability: Portability;
  model_provenance: { created_by_model?: string; retrieval_history?: RetrievalEvent[] } & Record<string, unknown>;
  usage_count: number;
  last_used_at: string | null;
}

export interface UsageBundle {
  memory_mau: number;
  ops: { ingest: number; retrieve: number; update: number; delete: number };
  storage_bytes: number;
  device_activations: number;
  migration_count: number;
}
