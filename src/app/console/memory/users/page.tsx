"use client";

import * as React from "react";
import {
  MoreHorizontal,
  Lock,
  ExternalLink,
  Check,
  Smartphone,
  Globe,
  Cpu,
  Eye,
  Search,
  Users as UsersIcon,
} from "lucide-react";
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
import { Input } from "@/components/ui/input";
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
  MemoryType,
  MemoryStatus,
  User,
} from "@/lib/types";
import { MemoryTraceSheet } from "@/components/memory/MemoryTraceSheet";

// ---- Config --------------------------------------------------------------

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
  needs_review: "Review",
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
  if (scope === "device_only") return <Smartphone className="size-3" strokeWidth={1.75} />;
  if (scope === "user_global") return <Globe className="size-3" strokeWidth={1.75} />;
  return null;
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

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ---- Page ----------------------------------------------------------------

export default function UsersPage() {
  const users = useMemoryStore((s) => s.users);
  const memories = useMemoryStore((s) => s.memories);
  const agents = useMemoryStore((s) => s.agents);
  const setMemoryStatus = useMemoryStore((s) => s.setMemoryStatus);
  const deleteMemory = useMemoryStore((s) => s.deleteMemory);

  const [selectedUserId, setSelectedUserId] = React.useState<string>(users[0]?.id ?? "");
  const [userQuery, setUserQuery] = React.useState("");
  const [typeFilter, setTypeFilter] = React.useState<"all" | MemoryType>("all");
  const [traceMemoryId, setTraceMemoryId] = React.useState<string | null>(null);
  const [traceOpen, setTraceOpen] = React.useState(false);

  const selectedUser: User | undefined = React.useMemo(
    () => users.find((u) => u.id === selectedUserId),
    [users, selectedUserId],
  );

  const filteredUsers = React.useMemo(() => {
    if (!userQuery.trim()) return users;
    const q = userQuery.toLowerCase();
    return users.filter(
      (u) =>
        u.display_name.toLowerCase().includes(q) ||
        u.passport_id.toLowerCase().includes(q) ||
        u.external_user_id.toLowerCase().includes(q),
    );
  }, [users, userQuery]);

  const userMemories = React.useMemo(() => {
    if (!selectedUser) return [];
    return memories
      .filter((m) => m.user_id === selectedUser.id)
      .filter((m) => (typeFilter === "all" ? true : m.type === typeFilter));
  }, [memories, selectedUser, typeFilter]);

  const agentName = React.useCallback(
    (id: string) => agents.find((a) => a.id === id)?.name ?? "—",
    [agents],
  );

  const openTrace = (id: string) => {
    setTraceMemoryId(id);
    setTraceOpen(true);
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-2xl font-medium tracking-tight">Users</h1>
          <Badge variant="outline" className="gap-1 font-mono text-[11px] tabular">
            <Lock className="size-2.5" />
            elevated
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          End users and their memories. Select a user to inspect, debug, and trace. Every view is logged.
        </p>
      </div>

      {/* Master-detail */}
      <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
        {/* User list (master) */}
        <Card className="h-fit lg:sticky lg:top-32">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Users</CardTitle>
              <span className="tabular text-xs text-muted-foreground">{users.length}</span>
            </div>
          </CardHeader>
          <CardContent className="px-2 pb-2">
            <div className="relative px-1 pb-2">
              <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
              <Input
                value={userQuery}
                onChange={(e) => setUserQuery(e.target.value)}
                placeholder="Search name or ID"
                className="h-8 pl-8 text-xs"
              />
            </div>
            <div className="max-h-[520px] space-y-0.5 overflow-y-auto ds-scroll px-1">
              {filteredUsers.map((u) => {
                const active = u.id === selectedUserId;
                const count = memories.filter((m) => m.user_id === u.id && m.status !== "deleted").length;
                return (
                  <button
                    key={u.id}
                    onClick={() => setSelectedUserId(u.id)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-lg p-2 text-left transition-colors",
                      active ? "bg-accent" : "hover:bg-accent/60",
                    )}
                  >
                    <Avatar className="size-8 shrink-0">
                      <AvatarFallback
                        className="text-[10px] font-medium text-white"
                        style={{ backgroundColor: u.avatar_color }}
                      >
                        {initials(u.display_name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium">{u.display_name}</p>
                      <p className="font-mono text-[10px] tabular text-muted-foreground">{u.passport_id}</p>
                    </div>
                    <span className="tabular shrink-0 text-[10px] text-muted-foreground">{count}</span>
                  </button>
                );
              })}
              {filteredUsers.length === 0 && (
                <p className="px-2 py-6 text-center text-xs text-muted-foreground">No users match.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* User detail (detail) */}
        <div className="space-y-4">
          {selectedUser && (
            <>
              {/* User header */}
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
                          <span className="text-base font-medium leading-tight">{selectedUser.display_name}</span>
                          <Badge variant="outline" className="font-mono text-[11px] tabular">
                            {selectedUser.passport_id}
                          </Badge>
                          <Badge
                            variant={selectedUser.age_group === "minor" ? "warning" : "secondary"}
                            className="text-[10px]"
                          >
                            {selectedUser.age_group}
                          </Badge>
                          <Badge
                            variant={selectedUser.memory_enabled ? "success" : "secondary"}
                            className="text-[10px]"
                          >
                            {selectedUser.memory_enabled ? "Memory ON" : "Memory OFF"}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          <span className="font-mono tabular text-foreground">
                            {memories.filter((m) => m.user_id === selectedUser.id && m.status !== "deleted").length}
                          </span>{" "}
                          memories · region {selectedUser.region} · joined {formatRelativeDay(selectedUser.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as "all" | MemoryType)}>
                        <SelectTrigger size="sm" className="w-[140px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {TYPE_OPTIONS.map((t) => (
                            <SelectItem key={t} value={t}>
                              {t === "all" ? "All types" : capitalize(t)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Memory records table — click row to open trace sheet */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Memory records</CardTitle>
                  <CardDescription>
                    Click any row to open its trace — what was retrieved, the projection, and which model did the retrieving.
                  </CardDescription>
                </CardHeader>
                <CardContent className="px-0 pb-0">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="pl-6 w-[110px]">Status</TableHead>
                        <TableHead className="w-[80px]">Type</TableHead>
                        <TableHead>Content</TableHead>
                        <TableHead className="w-[100px]">Scope</TableHead>
                        <TableHead className="w-[110px]">Portability</TableHead>
                        <TableHead className="w-[90px]">Used</TableHead>
                        <TableHead className="pr-4 w-[56px] text-right">·</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {userMemories.length === 0 && (
                        <TableRow className="hover:bg-transparent">
                          <TableCell colSpan={7} className="h-24 pl-6 text-center text-sm text-muted-foreground">
                            No memories match this filter.
                          </TableCell>
                        </TableRow>
                      )}
                      {userMemories.map((m) => (
                        <MemoryRow
                          key={m.id}
                          memory={m}
                          agentName={agentName(m.agent_id)}
                          onClickRow={() => openTrace(m.id)}
                          onArchive={() => {
                            setMemoryStatus(m.id, "archived");
                            toast(`Archived · ${m.id}`, { description: "Logged to audit trail." });
                          }}
                          onDelete={() => {
                            deleteMemory(m.id);
                            toast(`Deleted · ${m.id}`, { description: "Tombstone written. Logged to audit trail." });
                          }}
                          onViewSource={() =>
                            toast(`Source · ${m.id}`, { description: m.source.quote })
                          }
                        />
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {/* Safety note */}
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Lock className="size-3.5 shrink-0" strokeWidth={1.75} />
                <span>Sensitive content is masked by default. Every view writes the audit log.</span>
              </div>

              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <UsersIcon className="size-3.5 shrink-0" strokeWidth={1.75} />
                <span>
                  Identity is customer-owned (<span className="font-mono">external_user_id</span>).
                  <span className="font-mono">passport_id</span> is the user-ownership anchor.
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Trace drawer — opens on row click */}
      <MemoryTraceSheet
        memoryId={traceMemoryId}
        open={traceOpen}
        onOpenChange={setTraceOpen}
      />
    </div>
  );
}

// ---- Row -----------------------------------------------------------------

function MemoryRow({
  memory,
  agentName,
  onClickRow,
  onArchive,
  onDelete,
  onViewSource,
}: {
  memory: MemoryRecord;
  agentName: string;
  onClickRow: () => void;
  onArchive: () => void;
  onDelete: () => void;
  onViewSource: () => void;
}) {
  const portable = memory.portability.layer === "portable";
  const isDeleted = memory.status === "deleted";

  return (
    <TableRow
      className={cn("group cursor-pointer", isDeleted && "opacity-50")}
      onClick={onClickRow}
    >
      <TableCell className="pl-6">
        <span className="flex items-center gap-2">
          <span className={cn("size-2 rounded-full", statusDot[memory.status])} />
          <span className="text-[11px] text-muted-foreground">{statusLabel[memory.status]}</span>
        </span>
      </TableCell>

      <TableCell>
        <span className="text-xs font-medium capitalize">{memory.type}</span>
      </TableCell>

      <TableCell className="max-w-[280px]">
        <span className="block max-w-[280px] truncate font-medium text-sm" title={memory.content}>
          {memory.sensitivity === "S3" ? "••••• (masked · S3)" : memory.content}
        </span>
        <span className="text-[11px] text-muted-foreground">
          {agentName} · {memory.id}
        </span>
      </TableCell>

      <TableCell>
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          {scopeIcon(memory.scope)}
          {scopeLabel[memory.scope]}
        </span>
      </TableCell>

      <TableCell>
        {portable ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-primary">
            Portable <Check className="size-3" strokeWidth={2.5} />
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">Device-local</span>
        )}
      </TableCell>

      <TableCell>
        <span className="font-mono text-xs tabular">{memory.usage_count}×</span>
        {memory.last_used_at && (
          <span className="block text-[11px] text-muted-foreground">
            {formatRelativeDay(memory.last_used_at)}
          </span>
        )}
      </TableCell>

      <TableCell className="pr-4 text-right" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="Memory actions">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={onViewSource}>
              <Eye className="size-4" /> View source
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onClickRow}>
              <ExternalLink className="size-4" /> Open trace
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => toast("Edit mode", { description: "Inline edit would open here (prototype)." })}>
              <Cpu className="size-4" /> Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onArchive}>
              <Lock className="size-4" /> Archive
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onDelete} className="text-destructive focus:text-destructive">
              <span className="size-4 text-center text-base leading-none">×</span> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}
