import * as React from "react";
import { Check, X, Smartphone, Users, Shuffle, Globe, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Portability } from "@/lib/types";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";

const axes = [
  { key: "cross_device" as const, icon: Smartphone, label: "Cross-device" },
  { key: "cross_role" as const, icon: Users, label: "Cross-role" },
  { key: "cross_model" as const, icon: Shuffle, label: "Cross-model" },
  { key: "cross_brand_app" as const, icon: Globe, label: "Cross-brand app" },
];

/**
 * PortabilityBadges — materializes the portable-native data model as a visible
 * product feature. Users SEE which axes a memory travels on. This is the
 * "memory travels with me" concept made concrete (PRD §5.2.4).
 *
 * Two display modes:
 * - "full": a row of axis pills with ✓/✕ (used on Memory Detail)
 * - "compact": a single summary badge (used on MemoryCard)
 */
export function PortabilityBadges({
  portability,
  mode = "full",
  className,
}: {
  portability: Portability;
  mode?: "full" | "compact";
  className?: string;
}) {
  if (portability.layer === "device_local") {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div>
              <Badge variant="outline" className={cn("gap-1 text-[10px] text-muted-foreground", className)}>
                <Lock className="size-2.5" />
                Device-local
              </Badge>
            </div>
          </TooltipTrigger>
          <TooltipContent side="top">
            <p className="max-w-[200px] text-xs">
              Stays on this device only. Cannot travel.
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  if (mode === "compact") {
    const onCount = axes.filter((a) => portability[a.key]).length;
    return (
      <Badge variant="ink" className={cn("gap-1 text-[10px]", className)}>
        <Check className="size-2.5" />
        Portable · {onCount}/4
      </Badge>
    );
  }

  return (
    <TooltipProvider>
      <div className={cn("flex flex-wrap gap-1.5", className)}>
        {axes.map((a) => {
          const on = portability[a.key];
          const Icon = a.icon;
          return (
            <Tooltip key={a.key}>
              <TooltipTrigger asChild>
                <div
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
                    on
                      ? "border-ink-600/30 bg-ink-600/10 text-ink-700 dark:text-ink-300"
                      : "border-border bg-muted/50 text-muted-foreground",
                  )}
                >
                  <Icon className="size-2.5" strokeWidth={2} />
                  {on ? <Check className="size-2.5" /> : <X className="size-2.5 opacity-50" />}
                </div>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="text-xs">
                  {a.label}: {on ? "travels" : "stays"}
                </p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}
