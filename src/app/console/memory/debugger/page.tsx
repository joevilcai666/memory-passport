"use client";

import * as React from "react";
import Link from "next/link";
import { MoreHorizontal, Lock, ExternalLink, Check, Smartphone, Globe, Cpu, Eye } from "lucide-react";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useMemoryStore } from "@/store/memory-store";
import { cn, formatRelativeDay } from "@/lib/utils";
import type {
  MemoryRecord,
  MemoryScope,
  MemorySensitivity,
  MemoryStatus,
  MemoryType,
  User,
} from "@/lib/types";

// ---- Status / scope config ----------------------------------------------

const statusDot: Record<MemoryStatus, string> = {
  active: "bg-emerald-500",
  candidate: "bg-ink-500",
  needs_review: "bg-amber-500",
  archived: "bg-neutral-400",
  flagged_wrong: "bg-rose-500",
  deleted: "bg-rose-500",
  expired: "bg-neutral-400",
};

const statusLabel: Record<MemoryStatus, string> = {
  active: "Active",
  candidate: "Candidate",
  needs_review: "Needs review",
  archived: "Archived",
  flagged_wrong: "Flagged",
  deleted: "Deleted",
  expired: "Expired",
};

const scopeLabel: Record<MemoryScope, string> = {
  user_global: "Global",
  relationship_only: "Relationship",
  agent_only: "Agent",
  device_only: "Device",
  private: "Private",
  blocked: "Blocked",
};

function scopeIcon(scope: MemoryScope) {
  switch (scope) {
    case "device_only":
      return <Smartphone className="size-3" strokeWidth={1.75} />;
    case "user_global":
      return <Globe className="size-3" strokeWidth={1.75} />;
    default:
      return null;
  }
}

const TYPE_OPTIONS: ("all" | MemoryType)[] = [
  "all",
  "preference",
  "relationship",
  "event",
  "boundary",
  "task",
  "profile",
];

type StatusFilter = "active" | "all" | "archived";

// ---- Helpers --------------------------------------------------------------

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

const SENSITIVITY_OPTIONS: MemorySensitivity[] = ["S0", "S1", "S2", "S3"];

// ---- Filter chip ----------------------------------------------------------

function FilterChip({
  label,
  active,
  onClick,
  tone = "default",
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  tone?: "default" | "warn";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium transition-colors",
        active
          ? tone === "warn"
            ? "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400"
            : "border-primary/30 bg-primary/10 text-primary"
          : "border-border bg-background text-muted-foreground hover:bg-accent hover:text-foreground",
      )}
    >
      {active && <Check className="size-3" strokeWidth={2.5} />}
      {label}
    </button>
  );
}

// ---- Page -----------------------------------------------------------------

export default function MemoryDebuggerPage() {
  const users = useMemoryStore((s) => s.users);
  const memories = useMemoryStore((s) => s.memories);
  const agents = useMemoryStore((s) => s.agents);
  const setMemoryStatus = useMemoryStore((s) => s.setMemoryStatus);
  const deleteMemory = useMemoryStore((s) => s.deleteMemory);

  const [selectedUserId, setSelectedUserId] = React.useState<string>(users[0]?.id ?? "");
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>("active");
  const [typeFilter, setTypeFilter] = React.useState<"all" | MemoryType>("all");
  const [agentFilter, setAgentFilter] = React.useState<string>("all");
  const [sensitivityFilter, setSensitivityFilter] = React.useState<MemorySensitivity | null>(null);

  const selectedUser: User | undefined = React.useMemo(
    () => users.find((u) => u.id === selectedUserId),
    [users, selectedUserId],
  );

  const visibleMemories = React.useMemo(() => {
    if (!selectedUser) return [];
    return memories
      .filter((m) => m.user_id === selectedUser.id)
      .filter((m) => {
        if (statusFilter === "active") return m.status === "active";
        if (statusFilter === "archived") return m.status === "archived";
        return true; // all (incl. active/archived/candidate/needs_review/flagged)
      })
      .filter((m) => (typeFilter === "all" ? true : m.type === typeFilter))
      .filter((m) => (agentFilter === "all" ? true : m.agent_id === agentFilter))
      .filter((m) => (sensitivityFilter === null ? true : m.sensitivity === sensitivityFilter));
  }, [memories, selectedUser, statusFilter, typeFilter, agentFilter, sensitivityFilter]);

  const totalForUser = React.useMemo(
    () => (selectedUser ? memories.filter((m) => m.user_id === selectedUser.id).length : 0),
    [memories, selectedUser],
  );

  const agentName = React.useCallback(
    (id: string) => agents.find((a) => a.id === id)?.name ?? "—",
    [agents],
  );

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-2xl font-medium tracking-tight">Memory Debugger</h1>
          <Badge variant="outline" className="gap-1 font-mono text-[11px] tabular">
            <Lock className="size-2.5" />
            elevated
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Search a user to inspect their memories. Every view is logged.
        </p>
      </div>

      {/* Search / filter bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-2">
              <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                <SelectTrigger className="w-[280px]">
                  <SelectValue placeholder="Select a user" />
                </SelectTrigger>
                <SelectContent>
                  {users.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      <span className="flex items-center gap-2">
                        <span>{u.display_name}</span>
                        <span className="font-mono text-[11px] tabular text-muted-foreground">
                          {u.passport_id}
                        </span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Status: Active ▾  → segmented */}
              <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
                <SelectTrigger size="sm" className="w-[120px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>

              {/* Type ▾ */}
              <Select
                value={typeFilter}
                onValueChange={(v) => setTypeFilter(v as "all" | MemoryType)}
              >
                <SelectTrigger size="sm" className="w-[140px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  {TYPE_OPTIONS.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t === "all" ? "All types" : capitalize(t)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Agent ▾ */}
              <Select value={agentFilter} onValueChange={setAgentFilter}>
                <SelectTrigger size="sm" className="w-[150px]">
                  <SelectValue placeholder="Agent" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All agents</SelectItem>
                  {agents.map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      <span className="flex items-center gap-1.5">
                        <span>{a.emoji}</span>
                        <span>{a.name}</span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Sensitivity chips */}
              <div className="flex items-center gap-1.5">
                {SENSITIVITY_OPTIONS.map((s) => (
                  <FilterChip
                    key={s}
                    label={s}
                    tone={s === "S3" || s === "S2" ? "warn" : "default"}
                    active={sensitivityFilter === s}
                    onClick={() =>
                      setSensitivityFilter((prev) => (prev === s ? null : s))
                    }
                  />
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* User info header */}
      {selectedUser && (
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3.5">
                <Avatar className="size-11">
                  <AvatarFallback
                    className="text-sm font-medium text-white"
                    style={{ backgroundColor: selectedUser.avatar_color }}
                  >
                    {initials(selectedUser.display_name)}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-medium leading-tight">
                      {selectedUser.display_name}
                    </span>
                    <Badge variant="outline" className="font-mono text-[11px] tabular">
                      {selectedUser.passport_id}
                    </Badge>
                    <Badge
                      variant={selectedUser.age_group === "minor" ? "warning" : "secondary"}
                      className="text-[10px]"
                    >
                      {selectedUser.age_group}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    <span className="font-mono tabular text-foreground">{totalForUser}</span>{" "}
                    memories · joined {formatRelativeDay(selectedUser.created_at)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Cpu className="size-3.5 text-primary" strokeWidth={1.75} />
                <span className="font-mono tabular">
                  {visibleMemories.length} shown
                </span>
                <span className="text-border">/</span>
                <span className="font-mono tabular">{totalForUser} total</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Memory records table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Memory records</CardTitle>
          <CardDescription>
            {selectedUser
              ? `All memory records for ${selectedUser.display_name}.`
              : "Select a user to load records."}
          </CardDescription>
        </CardHeader>
        <CardContent className="px-0 pb-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-6 w-[120px]">Status</TableHead>
                <TableHead className="w-[90px]">Type</TableHead>
                <TableHead>Content</TableHead>
                <TableHead className="w-[110px]">Scope</TableHead>
                <TableHead className="w-[120px]">Portability</TableHead>
                <TableHead className="w-[120px]">Used</TableHead>
                <TableHead className="pr-4 w-[56px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleMemories.length === 0 && (
                <TableRow className="hover:bg-transparent">
                  <TableCell colSpan={7} className="h-24 pl-6 text-center text-sm text-muted-foreground">
                    No memories match these filters.
                  </TableCell>
                </TableRow>
              )}
              {visibleMemories.map((m) => (
                <MemoryRow
                  key={m.id}
                  memory={m}
                  agentName={agentName(m.agent_id)}
                  onArchive={() => {
                    setMemoryStatus(m.id, "archived");
                    toast(`Archived · ${m.id}`, {
                      description: "Memory moved to archived. Logged to audit trail.",
                    });
                  }}
                  onDelete={() => {
                    deleteMemory(m.id);
                    toast(`Deleted · ${m.id}`, {
                      description: "Tombstone written. Logged to audit trail.",
                    });
                  }}
                />
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Safety note */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Lock className="size-3.5 shrink-0" strokeWidth={1.75} />
        <span>
          Sensitive content is masked by default. Every view writes the audit log.
        </span>
      </div>
    </div>
  );
}

// ---- Row ------------------------------------------------------------------

function MemoryRow({
  memory,
  agentName,
  onArchive,
  onDelete,
}: {
  memory: MemoryRecord;
  agentName: string;
  onArchive: () => void;
  onDelete: () => void;
}) {
  const portable = memory.portability.layer === "portable";
  const isDeleted = memory.status === "deleted";

  return (
    <TableRow className={cn("group", isDeleted && "opacity-50")}>
      {/* Status */}
      <TableCell className="pl-6">
        <span className="flex items-center gap-2">
          <span className={cn("size-2 rounded-full", statusDot[memory.status])} />
          <span className="text-[11px] text-muted-foreground">
            {statusLabel[memory.status]}
          </span>
        </span>
      </TableCell>

      {/* Type */}
      <TableCell>
        <span className="text-xs font-medium capitalize">{memory.type}</span>
      </TableCell>

      {/* Content */}
      <TableCell className="max-w-[280px]">
        <span className="block max-w-[280px] truncate font-medium text-sm" title={memory.content}>
          {memory.sensitivity === "S3" ? "••••• (masked · S3)" : memory.content}
        </span>
        <span className="text-[11px] text-muted-foreground">
          {agentName} · {memory.id}
        </span>
      </TableCell>

      {/* Scope */}
      <TableCell>
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          {scopeIcon(memory.scope)}
          {scopeLabel[memory.scope]}
        </span>
      </TableCell>

      {/* Portability */}
      <TableCell>
        {portable ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-primary">
            Portable
            <Check className="size-3" strokeWidth={2.5} />
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">Device-local</span>
        )}
      </TableCell>

      {/* Used */}
      <TableCell>
        <span className="font-mono text-xs tabular">{memory.usage_count}×</span>
        {memory.last_used_at && (
          <span className="block text-[11px] text-muted-foreground">
            {formatRelativeDay(memory.last_used_at)}
          </span>
        )}
      </TableCell>

      {/* Actions */}
      <TableCell className="pr-4 text-right">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="Memory actions">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem
              onClick={() =>
                toast(`Source · ${memory.id}`, {
                  description: memory.source.quote,
                })
              }
            >
              <Eye className="size-4" />
              View source
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href={`/console/memory/debugger/${memory.id}/trace`}>
                <ExternalLink className="size-4" />
                Open trace
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() =>
                toast("Edit mode", {
                  description: "Inline edit would open here (prototype).",
                })
              }
            >
              <Cpu className="size-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onArchive}>
              <Lock className="size-4" />
              Archive
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={onDelete}
              className="text-destructive focus:text-destructive"
            >
              <span className="size-4 text-center text-base leading-none">×</span>
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}
