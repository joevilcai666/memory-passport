"use client";

import * as React from "react";
import { ArrowUpRight, ArrowDownRight, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function KpiTile({
  label,
  value,
  delta,
  deltaPositive = true,
  icon: Icon,
  format = "plain",
  className,
}: {
  label: string;
  value: number | string;
  delta?: string;
  deltaPositive?: boolean;
  icon?: LucideIcon;
  format?: "plain" | "percent" | "number";
  className?: string;
}) {
  const display =
    typeof value === "number"
      ? format === "percent"
        ? `${(value * 100).toFixed(1)}%`
        : format === "number"
          ? value.toLocaleString("en-US")
          : String(value)
      : value;

  return (
    <div className={cn("rounded-xl border bg-card p-5 shadow-sm", className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        {Icon && <Icon className="size-4 text-muted-foreground/70" strokeWidth={1.5} />}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="tabular text-2xl font-semibold tracking-tight">{display}</span>
        {delta && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 text-xs font-medium",
              deltaPositive ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400",
            )}
          >
            {deltaPositive ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}
            {delta}
          </span>
        )}
      </div>
    </div>
  );
}
