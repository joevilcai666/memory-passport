"use client";

import * as React from "react";
import Link from "next/link";
import { Plus, Download, Trash2, Smartphone, Pause, Play, MoreHorizontal, Search } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { MemoryCard } from "@/components/memory/MemoryCard";
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
  const { memories, currentUser, toggleMemoryEnabled } = useMemoryStore();
  const [filter, setFilter] = React.useState<MemoryType | "all" | "archived">("all");
  const [query, setQuery] = React.useState("");

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

  const handlePause = () => {
    toggleMemoryEnabled();
    toast(memoryOn ? "Memory paused" : "Memory is on", {
      description: memoryOn ? "Luna won't write new memories." : "Luna will remember again.",
    });
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
            <DropdownMenuItem onClick={() => toast.success("Export started", { description: "42 memories · JSON" })}>
              <Download className="size-3.5" /> Export
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
          <Button variant="outline" size="sm" className="flex-1" onClick={handlePause}>
            {memoryOn ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
            {memoryOn ? "Pause" : "Resume"}
          </Button>
          <Button variant="outline" size="sm" className="flex-1" onClick={() => toast("Tell Luna to remember something", { description: "Try: \"Remember that I prefer…\"" })}>
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
    </AppShell>
  );
}
