"use client";

import Link from "next/link";
import { MessageSquare, Mic, Settings2, Bot, Cpu, CalendarClock } from "lucide-react";
import { cn, formatRelativeDay } from "@/lib/utils";
import type { MemoryRecord } from "@/lib/types";
import { PortabilityBadges } from "./PortabilityBadges";
import { Badge } from "@/components/ui/badge";

const typeConfig: Record<MemoryRecord["type"], { label: string; color: string }> = {
  preference: { label: "Preference", color: "text-emerald-600 dark:text-emerald-400" },
  relationship: { label: "Relationship", color: "text-violet-600 dark:text-violet-400" },
  event: { label: "Event", color: "text-amber-600 dark:text-amber-400" },
  boundary: { label: "Boundary", color: "text-rose-600 dark:text-rose-400" },
  task: { label: "Task", color: "text-foreground/70" },
  profile: { label: "Profile", color: "text-ink-600 dark:text-ink-400" },
};

const sourceIcon: Record<MemoryRecord["source"]["source_type"], typeof MessageSquare> = {
  chat: MessageSquare,
  voice: Mic,
  setup: Settings2,
  explicit_instruction: Settings2,
  robot_event: Cpu,
  app_event: Bot,
};

export function MemoryCard({
  memory,
  href,
  className,
}: {
  memory: MemoryRecord;
  href?: string;
  className?: string;
}) {
  const tc = typeConfig[memory.type];
  const SIcon = sourceIcon[memory.source.source_type] ?? MessageSquare;
  const linkHref = href ?? `/app/memory/${memory.id}`;
  const isDimmed = memory.status === "archived" || memory.status === "deleted";

  return (
    <Link
      href={linkHref}
      className={cn(
        "group block rounded-xl border bg-card p-4 shadow-sm transition-all hover:border-primary/30 hover:shadow-md",
        isDimmed && "opacity-60",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium leading-snug text-foreground">{memory.content}</p>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-muted-foreground">
            <span className={cn("font-medium", tc.color)}>{tc.label}</span>
            <span className="inline-flex items-center gap-1">
              <SIcon className="size-3" strokeWidth={1.5} />
              {memory.source.source_type === "explicit_instruction" ? "you said" : memory.source.source_type}
            </span>
            <span className="inline-flex items-center gap-1">
              <CalendarClock className="size-3" strokeWidth={1.5} />
              {memory.last_used_at ? `used ${formatRelativeDay(memory.last_used_at)}` : formatRelativeDay(memory.source.timestamp)}
            </span>
          </div>
        </div>
        <PortabilityBadges portability={memory.portability} mode="compact" />
      </div>
      {memory.status === "needs_review" && (
        <div className="mt-3">
          <Badge variant="warning" className="text-[10px]">Needs review</Badge>
        </div>
      )}
    </Link>
  );
}
