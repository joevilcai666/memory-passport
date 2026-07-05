import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { StampMark } from "./StampMark";

/**
 * PoweredByMemoryPassport — the co-brand watermark.
 *
 * From PRD §3.4: this MUST appear on every user-facing surface (consent,
 * Memory Center footer, migration complete). It's the seed of the network
 * effect — "portability moat needs C-side awareness, awareness needs brand
 * visibility, co-branding is planted in V0.1."
 *
 * Appears as a small, honest mark. Never loud.
 */
export function PoweredByMemoryPassport({
  className,
  align = "center",
}: {
  className?: string;
  align?: "center" | "start";
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-xs text-muted-foreground",
        align === "center" ? "justify-center" : "justify-start",
        className,
      )}
    >
      <span className="text-[10px] uppercase tracking-[0.14em] font-medium opacity-70">
        Powered by
      </span>
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 font-medium text-foreground/80 transition-colors hover:text-primary"
      >
        <StampMark className="size-4 text-primary" />
        <span>Memory Passport</span>
      </Link>
    </div>
  );
}
