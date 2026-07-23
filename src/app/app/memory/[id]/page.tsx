"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Pencil,
  Trash2,
  Flag,
  MessageSquare,
  Mic,
  Settings2,
  Cpu,
  Bot,
  Check,
  ShieldAlert,
  History,
  Loader2,
} from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PortabilityBadges } from "@/components/memory/PortabilityBadges";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useMemoryStore } from "@/store/memory-store";
import { formatDate, formatRelativeDay, cn } from "@/lib/utils";
import type { MemoryRecord } from "@/lib/types";
import { toast } from "sonner";

const sourceIcon = {
  chat: MessageSquare,
  voice: Mic,
  setup: Settings2,
  explicit_instruction: Settings2,
  robot_event: Cpu,
  app_event: Bot,
} as const;

export default function MemoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { memories, devices, editMemory, deleteMemory, setMemoryStatus, dataMode } = useMemoryStore();

  const memory = memories.find((m) => m.id === id);

  const [editOpen, setEditOpen] = React.useState(false);
  const [editText, setEditText] = React.useState("");
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [activeAction, setActiveAction] = React.useState<"edit" | "delete" | "report" | null>(null);

  if (!memory) {
    return (
      <AppShell title="Memory" backHref="/app/memory">
        <div className="rounded-xl border border-dashed py-16 text-center">
          <p className="text-sm font-medium">Memory not found</p>
          <p className="mt-1 text-xs text-muted-foreground">It may have been deleted.</p>
          <Button variant="outline" size="sm" className="mt-4" asChild>
            <Link href="/app/memory">Back to Memory Center</Link>
          </Button>
        </div>
      </AppShell>
    );
  }

  const SIcon = sourceIcon[memory.source.source_type] ?? MessageSquare;
  const usedByDevices = devices.filter((d) => d.status === "bound");
  const confidenceLabel =
    memory.confidence >= 0.9 ? "High" : memory.confidence >= 0.75 ? "Medium" : "Low";

  const handleEdit = async () => {
    setActiveAction("edit");
    try {
      const saved = await editMemory(memory.id, editText.trim());
      setEditOpen(false);
      router.replace(`/app/memory/${encodeURIComponent(saved.id)}`);
      toast.success("Memory updated", {
        description: `Luna will use server version v${saved.version}.`,
      });
    } catch (error) {
      toast.error("Could not update memory", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setActiveAction(null);
    }
  };

  const handleDelete = async () => {
    setActiveAction("delete");
    try {
      await deleteMemory(memory.id);
      setDeleteOpen(false);
      toast.success("Memory deleted", { description: "Removed from Luna's recall." });
      router.push("/app/memory");
    } catch (error) {
      toast.error("Could not delete memory", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setActiveAction(null);
    }
  };

  const handleReport = async () => {
    setActiveAction("report");
    try {
      await setMemoryStatus(memory.id, "flagged_wrong");
      toast.success("Reported as wrong", {
        description: "Luna will stop using it while reviewed.",
      });
    } catch (error) {
      toast.error("Could not report memory", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setActiveAction(null);
    }
  };

  return (
    <AppShell title="Memory" backHref="/app/memory">
      <div className="space-y-5">
        {/* The memory content */}
        <div className="rounded-2xl border bg-card p-5">
          <p className="text-[17px] font-medium leading-snug text-foreground">{memory.content}</p>
          {memory.status === "needs_review" && (
            <Badge variant="warning" className="mt-3 gap-1">
              <ShieldAlert className="size-3" /> Needs review
            </Badge>
          )}
        </div>

        {/* Portability — the productized visibility */}
        <div className="rounded-2xl border bg-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Portability</p>
            {memory.portability.layer === "portable" ? (
              <Badge variant="ink" className="gap-1 text-[10px]">
                <Check className="size-2.5" /> Travels with you
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px]">Stays on this device</Badge>
            )}
          </div>
          <PortabilityBadges portability={memory.portability} mode="full" />
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            {memory.portability.layer === "portable"
              ? "This memory follows you across devices, AI roles, and models."
              : "This memory is tied to this device and cannot be migrated. Typically sensor data or device-specific state."}
          </p>
        </div>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-3">
          <MetaCard label="Type" value={memory.type.charAt(0).toUpperCase() + memory.type.slice(1)} />
          <MetaCard label="Scope" value={scopeLabel(memory.scope)} />
          <MetaCard label="Confidence" value={confidenceLabel} />
          <MetaCard label="Created" value={formatDate(memory.source.timestamp)} />
          <MetaCard label="Last used" value={memory.last_used_at ? formatRelativeDay(memory.last_used_at) : "Never"} />
          <MetaCard label="Times used" value={String(memory.usage_count)} mono />
        </div>

        {/* Why was this saved? — the transparency requirement */}
        <div className="rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Why was this saved?
          </p>
          <div className="mt-3 flex items-start gap-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted">
              <SIcon className="size-4 text-muted-foreground" strokeWidth={1.5} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm leading-relaxed text-foreground">
                &ldquo;{memory.source.quote}&rdquo;
              </p>
              <p className="mt-1.5 text-xs text-muted-foreground">
                {memory.source.source_type === "explicit_instruction"
                  ? "You explicitly told Luna to remember this."
                  : `From a ${memory.source.source_type.replace("_", " ")} · ${formatDate(memory.source.timestamp)}`}
              </p>
            </div>
          </div>
        </div>

        {/* Used by */}
        <div className="rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Used by</p>
          <div className="mt-3 space-y-2.5">
            <UsedByRow icon={Bot} label="Luna iOS App" on />
            {usedByDevices.map((d) => (
              <UsedByRow key={d.id} icon={Cpu} label={`${d.model} ${d.generation}`} on />
            ))}
            {memory.model_provenance.retrieval_history.some((r) => r.used) && (
              <div className="border-t pt-2.5">
                <p className="mb-2 text-[11px] text-muted-foreground">Retrieved by models</p>
                {memory.model_provenance.retrieval_history
                  .filter((r) => r.used)
                  .slice(-3)
                  .map((r, i) => (
                    <div key={i} className="flex items-center gap-2 py-1 text-xs">
                      <Check className="size-3 text-emerald-500" />
                      <span className="font-mono">{r.model}</span>
                      <span className="ml-auto text-muted-foreground">{formatRelativeDay(r.timestamp)}</span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-3 gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={activeAction !== null || dataMode !== "live"}
            onClick={() => {
              setEditText(memory.content);
              setEditOpen(true);
            }}
          >
            <Pencil className="size-3.5" /> Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={activeAction !== null || dataMode !== "live"}
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="size-3.5" /> Delete
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleReport}
            disabled={activeAction !== null || dataMode !== "live"}
          >
            {activeAction === "report" ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Flag className="size-3.5" />
            )}
            {activeAction === "report" ? "Reporting..." : "Report"}
          </Button>
        </div>

        {/* Version history */}
        {memory.version > 1 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <History className="size-3.5" />
            Edited {memory.version} times · v{memory.version}
          </div>
        )}
      </div>

      {/* Edit dialog */}
      <Dialog open={editOpen} onOpenChange={(open) => activeAction !== "edit" && setEditOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit memory</DialogTitle>
            <DialogDescription>Luna will use your edited version going forward.</DialogDescription>
          </DialogHeader>
          <label htmlFor="memory-content" className="sr-only">Memory content</label>
          <Textarea
            id="memory-content"
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={3}
            disabled={activeAction === "edit"}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)} disabled={activeAction === "edit"}>Cancel</Button>
            <Button onClick={handleEdit} disabled={!editText.trim() || activeAction === "edit"}>
              {activeAction === "edit" ? <Loader2 className="size-4 animate-spin" /> : null}
              {activeAction === "edit" ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete dialog */}
      <Dialog open={deleteOpen} onOpenChange={(open) => activeAction !== "delete" && setDeleteOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this memory?</DialogTitle>
            <DialogDescription>
              Luna will stop using it in future conversations. This is recorded in the audit log.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-lg border bg-muted/50 p-3">
            <p className="text-sm text-foreground">{memory.content}</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={activeAction === "delete"}>Keep</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={activeAction === "delete"}>
              {activeAction === "delete" ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Trash2 className="size-3.5" />
              )}
              {activeAction === "delete" ? "Deleting..." : "Delete forever"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}

function MetaCard({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-xl border bg-card p-3">
      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-sm font-medium capitalize", mono && "tabular")}>{value}</p>
    </div>
  );
}

function UsedByRow({ icon: Icon, label, on }: { icon: typeof Bot; label: string; on: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex size-7 items-center justify-center rounded-lg bg-muted">
        <Icon className="size-3.5 text-muted-foreground" strokeWidth={1.5} />
      </div>
      <span className="text-sm">{label}</span>
      {on && (
        <div className="ml-auto flex size-5 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-600">
          <Check className="size-3" strokeWidth={2.5} />
        </div>
      )}
    </div>
  );
}

function scopeLabel(scope: MemoryRecord["scope"]): string {
  return {
    user_global: "All of Luna",
    relationship_only: "Luna only",
    agent_only: "This role only",
    device_only: "This device only",
    private: "Private",
    blocked: "Blocked",
  }[scope];
}
