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
  | "failed";

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
  old_device_access: OldDeviceAccess;
  audit_log_id: ID | null;
  created_at: string;
  completed_at: string | null;
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
  | "memory.exported"
  | "app.created"
  | "agent.created"
  | "user.created"
  | "relationship.created"
  | "device.registered";

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
  last_active: string;
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
