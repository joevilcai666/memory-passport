"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useMemoryStore } from "@/store/memory-store";

interface TooltipPayloadEntry {
  dataKey: string;
  value: number;
  color: string;
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-medium">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="size-2 rounded-full" style={{ background: p.color }} />
          <span className="capitalize text-muted-foreground">{p.dataKey}:</span>
          <span className="tabular font-medium">{p.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

export function ActivityChart() {
  const data = useMemoryStore((s) => s.activity);
  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="gradReads" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.25} />
              <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradWrites" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-chart-2)" stopOpacity={0.22} />
              <stop offset="100%" stopColor="var(--color-chart-2)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} opacity={0.6} />
          <XAxis
            dataKey="day"
            stroke="var(--color-muted-foreground)"
            tickLine={false}
            axisLine={false}
            fontSize={12}
          />
          <YAxis
            stroke="var(--color-muted-foreground)"
            tickLine={false}
            axisLine={false}
            fontSize={12}
            width={48}
            tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--color-border)", strokeWidth: 1 }} />
          <Area
            type="monotone"
            dataKey="reads"
            stroke="var(--color-chart-1)"
            strokeWidth={2}
            fill="url(#gradReads)"
          />
          <Area
            type="monotone"
            dataKey="writes"
            stroke="var(--color-chart-2)"
            strokeWidth={2}
            fill="url(#gradWrites)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
