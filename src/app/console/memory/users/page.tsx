"use client";

import * as React from "react";
import {
  MoreHorizontal,
  Lock,
  ExternalLink,
  Check,
  Smartphone,
  Globe,
  Pencil,
  Eye,
  Users as UsersIcon,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

import {
  Card,
  CardContent,
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
  MemoryType,
  MemoryStatus,
  User,
} from "@/lib/types";
import { MemoryTraceSheet } from "@/components/memory/MemoryTraceSheet";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
  const editMemory = useMemoryStore((s) => s.editMemory);
  const dataMode = useMemoryStore((s) => s.dataMode);

  const [selectedUserId, setSelectedUserId] = React.useState<string>(users[0]?.id ?? "");
  const [typeFilter, setTypeFilter] = React.useState<"all" | MemoryType>("all");
  const [traceMemoryId, setTraceMemoryId] = React.useState<string | null>(null);
  const [traceOpen, setTraceOpen] = React.useState(false);
  const [editingMemoryId, setEditingMemoryId] = React.useState<string | null>(null);
  const [editText, setEditText] = React.useState("");
  const [busyMemoryId, setBusyMemoryId] = React.useState<string | null>(null);

  const selectedUser: User | undefined = React.useMemo(
    () => users.find((u) => u.id === selectedUserId),
    [users, selectedUserId],
  );

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

  const startEdit = (memory: MemoryRecord) => {
    setEditingMemoryId(memory.id);
    setEditText(memory.content);
  };

  const handleEdit = async () => {
    const memoryId = editingMemoryId;
    const content = editText.trim();
    if (!memoryId || !content) return;

    setBusyMemoryId(memoryId);
    try {
      await editMemory(memoryId, content);
      setEditingMemoryId(null);
      toast.success("Memory updated", { description: `${memoryId} now uses the new version.` });
    } catch (error) {
      toast.error("Memory update failed", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setBusyMemoryId(null);
    }
  };

  const handleArchive = async (memory: MemoryRecord) => {
    setBusyMemoryId(memory.id);
    try {
      await setMemoryStatus(memory.id, "archived");
      toast.success(`Archived · ${memory.id}`, { description: "Logged to audit trail." });
    } catch (error) {
      toast.error("Archive failed", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setBusyMemoryId(null);
    }
  };

  const handleDelete = async (memory: MemoryRecord) => {
    setBusyMemoryId(memory.id);
    try {
      await deleteMemory(memory.id);
      toast.success(`Deleted · ${memory.id}`, {
        description: "Tombstone written. Logged to audit trail.",
      });
    } catch (error) {
      toast.error("Delete failed", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setBusyMemoryId(null);
    }
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

      {/* User picker + memory records — full-width single column.
          The user header and the table live in one card so the table
          gets maximum width. Switching users happens via the Select. */}
      {selectedUser && (
        <Card>
          {/* User header with inline user-switcher + filters */}
          <CardContent className="border-b p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
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
                    {/* Inline user switcher — search by name / passport_id / external_id */}
                    <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                      <SelectTrigger className="h-8 w-[200px] gap-2 text-base font-medium">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {users.map((u) => (
                          <SelectItem key={u.id} value={u.id}>
                            <span className="flex items-center gap-2">
                              <span>{u.display_name}</span>
                              <span className="font-mono text-[10px] tabular text-muted-foreground">
                                {u.passport_id}
                              </span>
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
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

              {/* Filters */}
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

          {/* Memory records table — full width, click row to open trace sheet */}
          <div className="px-0 pb-0">
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
                    onEdit={() => startEdit(m)}
                    onArchive={() => handleArchive(m)}
                    onDelete={() => handleDelete(m)}
                    onViewSource={() =>
                      toast(`Source · ${m.id}`, { description: m.source.quote })
                    }
                    busy={busyMemoryId === m.id}
                    writesEnabled={dataMode === "live"}
                  />
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}

      {/* Helper row: how to read this page */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Lock className="size-3.5 shrink-0" strokeWidth={1.75} />
          <span>Sensitive content is masked by default. Every view writes the audit log.</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <UsersIcon className="size-3.5 shrink-0" strokeWidth={1.75} />
          <span>
            <span className="font-mono">external_user_id</span> is customer-owned ·{" "}
            <span className="font-mono">passport_id</span> is the ownership anchor
          </span>
        </div>
      </div>

      {/* Trace drawer — opens on row click */}
      <MemoryTraceSheet
        memoryId={traceMemoryId}
        open={traceOpen}
        onOpenChange={setTraceOpen}
      />

      <Dialog
        open={editingMemoryId !== null}
        onOpenChange={(open) => !busyMemoryId && !open && setEditingMemoryId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit memory</DialogTitle>
            <DialogDescription>
              Saving creates a new version and records the change in the audit log.
            </DialogDescription>
          </DialogHeader>
          <label htmlFor="console-memory-content" className="text-sm font-medium">
            Memory content
          </label>
          <Textarea
            id="console-memory-content"
            value={editText}
            onChange={(event) => setEditText(event.target.value)}
            disabled={busyMemoryId !== null}
            rows={4}
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditingMemoryId(null)}
              disabled={busyMemoryId !== null}
            >
              Cancel
            </Button>
            <Button onClick={handleEdit} disabled={!editText.trim() || busyMemoryId !== null}>
              {busyMemoryId ? <Loader2 className="size-4 animate-spin" /> : null}
              {busyMemoryId ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---- Row -----------------------------------------------------------------

function MemoryRow({
  memory,
  agentName,
  onClickRow,
  onEdit,
  onArchive,
  onDelete,
  onViewSource,
  busy,
  writesEnabled,
}: {
  memory: MemoryRecord;
  agentName: string;
  onClickRow: () => void;
  onEdit: () => void;
  onArchive: () => void;
  onDelete: () => void;
  onViewSource: () => void;
  busy: boolean;
  writesEnabled: boolean;
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
            <Button variant="ghost" size="icon-sm" aria-label="Memory actions" disabled={busy}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : <MoreHorizontal className="size-4" />}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={onViewSource}>
              <Eye className="size-4" /> View source
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onClickRow}>
              <ExternalLink className="size-4" /> Open trace
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onEdit} disabled={!writesEnabled || isDeleted}>
              <Pencil className="size-4" /> Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onArchive} disabled={!writesEnabled || isDeleted || memory.status === "archived"}>
              <Lock className="size-4" /> Archive
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onDelete} disabled={!writesEnabled || isDeleted} className="text-destructive focus:text-destructive">
              <span className="size-4 text-center text-base leading-none">×</span> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}
