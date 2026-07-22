"use client";

import * as React from "react";
import Link from "next/link";
import { Plus, Download, Trash2, Smartphone, Pause, Play, MoreHorizontal, Search, Loader2 } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MemoryCard } from "@/components/memory/MemoryCard";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { useMemoryStore } from "@/store/memory-store";
import { cn } from "@/lib/utils";
import type { MemoryType } from "@/lib/types";
import { toast } from "sonner";

const typeFilters: { value: MemoryType | "all" | "archived"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "preference", label: "Preferences" },
  { value: "relationship", label: "Relationship" },
  { value: "event", label: "Events" },
  { value: "boundary", label: "Boundaries" },
  { value: "task", label: "Tasks" },
  { value: "archived", label: "Archived" },
];

export default function MemoryCenterPage() {
  const { memories, currentUser, setMemoryEnabled, addMemory, exportMemories, dataMode } =
    useMemoryStore();
  const [filter, setFilter] = React.useState<MemoryType | "all" | "archived">("all");
  const [query, setQuery] = React.useState("");
  const [consentSaving, setConsentSaving] = React.useState(false);
  const [addOpen, setAddOpen] = React.useState(false);
  const [newMemory, setNewMemory] = React.useState("");
  const [adding, setAdding] = React.useState(false);
  const [exporting, setExporting] = React.useState(false);

  const memoryOn = currentUser.memory_enabled;

  const counts = React.useMemo(() => {
    const c: Record<string, number> = { all: 0, archived: 0 };
    memories.forEach((m) => {
      if (m.status === "deleted") return;
      if (m.status === "archived") c.archived++;
      else {
        c.all++;
        c[m.type] = (c[m.type] || 0) + 1;
      }
    });
    return c;
  }, [memories]);

  const visible = React.useMemo(() => {
    return memories.filter((m) => {
      if (m.status === "deleted") return false;
      if (filter === "all") return m.status !== "archived";
      if (filter === "archived") return m.status === "archived";
      return m.type === filter && m.status !== "archived";
    }).filter((m) =>
      query.trim() ? m.content.toLowerCase().includes(query.toLowerCase()) : true,
    );
  }, [memories, filter, query]);

  const handlePause = async () => {
    setConsentSaving(true);
    try {
      await setMemoryEnabled(!memoryOn);
      toast.success(memoryOn ? "Memory paused" : "Memory is on", {
        description: memoryOn ? "Luna won't write new memories." : "Luna will remember again.",
      });
    } catch (error) {
      toast.error(memoryOn ? "Could not pause memory" : "Could not resume memory", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setConsentSaving(false);
    }
  };

  const handleAddMemory = async () => {
    const content = newMemory.trim();
    if (!content) return;
    setAdding(true);
    try {
      await addMemory(content, "preference");
      setNewMemory("");
      setAddOpen(false);
      toast.success("Memory saved", { description: "Luna can now use this explicit memory." });
    } catch (error) {
      toast.error("Could not save memory", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setAdding(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const result = await exportMemories();
      const url = URL.createObjectURL(result.blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `memory-passport-${result.export_id}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success("Export downloaded", { description: `${counts.all} active memories · JSON` });
    } catch (error) {
      toast.error("Could not export memories", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setExporting(false);
    }
  };

  return (
    <AppShell
      headerCenter={
        <div className="flex items-center gap-2">
          <span>Memory</span>
          <Badge
            variant={memoryOn ? "success" : "secondary"}
            className="gap-1 text-[10px]"
          >
            <span className={cn("size-1.5 rounded-full", memoryOn ? "bg-emerald-500 animate-pulse" : "bg-muted-foreground")} />
            {memoryOn ? "ON" : "Paused"}
          </Badge>
        </div>
      }
      backHref="/"
      actions={
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="More">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link href="/app/devices">
                <Smartphone className="size-3.5" /> Devices
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleExport} disabled={exporting || dataMode !== "live"}>
              {exporting ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Download className="size-3.5" />
              )}
              Export
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/app/memory/delete" className="text-rose-600 focus:text-rose-700">
                <Trash2 className="size-3.5" /> Delete all memory
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      }
    >
      <div className="space-y-5">
        {/* Count + ownership */}
        <div>
          <p className="text-sm text-muted-foreground">
            <span className="tabular text-base font-semibold text-foreground">{counts.all}</span> {counts.all === 1 ? "thing" : "things"} Luna remembers about you.
          </p>
          <p className="mt-1 text-xs text-muted-foreground/80">
            These memories belong to you.
          </p>
        </div>

        {/* Pause / Add */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={handlePause}
            disabled={consentSaving || dataMode !== "live"}
          >
            {consentSaving ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : memoryOn ? (
              <Pause className="size-3.5" />
            ) : (
              <Play className="size-3.5" />
            )}
            {consentSaving ? (memoryOn ? "Pausing..." : "Resuming...") : memoryOn ? "Pause" : "Resume"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => setAddOpen(true)}
            disabled={dataMode !== "live"}
          >
            <Plus className="size-3.5" />
            Tell Luna
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories"
            className="h-9 pl-9"
          />
        </div>

        {/* Category chips */}
        <div className="-mx-5 flex gap-1.5 overflow-x-auto px-5 pb-1 ds-scroll">
          {typeFilters.map((f) => {
            const count = counts[f.value] ?? 0;
            if (f.value !== "all" && f.value !== "archived" && count === 0) return null;
            const active = filter === f.value;
            return (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={cn(
                  "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                  active
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:text-foreground",
                )}
              >
                {f.label}
                <span className={cn("tabular text-[10px]", active ? "opacity-80" : "opacity-60")}>{count}</span>
              </button>
            );
          })}
        </div>

        {/* Memory list */}
        <div className="space-y-2.5">
          {visible.length === 0 ? (
            <div className="rounded-xl border border-dashed py-12 text-center">
              <p className="text-sm font-medium">No memories here yet</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {query ? "Try a different search." : "Talk to Luna and memories will appear."}
              </p>
            </div>
          ) : (
            visible.map((m) => <MemoryCard key={m.id} memory={m} />)
          )}
        </div>
      </div>

      <Dialog open={addOpen} onOpenChange={(open) => !adding && setAddOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Tell Luna to remember</DialogTitle>
            <DialogDescription>
              This creates an explicit memory in your Passport. You can edit or delete it later.
            </DialogDescription>
          </DialogHeader>
          <label htmlFor="new-memory" className="text-sm font-medium">
            Memory to save
          </label>
          <Textarea
            id="new-memory"
            value={newMemory}
            onChange={(event) => setNewMemory(event.target.value)}
            placeholder="I prefer jasmine tea."
            rows={3}
            disabled={adding}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)} disabled={adding}>
              Cancel
            </Button>
            <Button onClick={handleAddMemory} disabled={!newMemory.trim() || adding}>
              {adding ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
              {adding ? "Saving..." : "Remember this"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
