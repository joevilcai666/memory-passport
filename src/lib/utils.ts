import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes with conflict resolution. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format an ISO date string to "Jun 12, 2026". */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Format an ISO date string to "Jun 12, 2026 · 14:32". */
export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return `${formatDate(iso)} · ${d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })}`;
}

/** Relative-ish short label: "Today", "Yesterday", or "Mon D". */
export function formatRelativeDay(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const dayMs = 86400000;
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfDay = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((startOfToday - startOfDay) / dayMs);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff > 1 && diff < 7) return `${diff} days ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Format a number with thousands separators. */
export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

/** Format a 0-1 float as a percentage with one decimal. */
export function formatPercent(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}
